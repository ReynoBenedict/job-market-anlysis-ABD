from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from talentscope.ingestion.connectors.lake_vacancies import (
    IMPLAUSIBLE_SALARY_TEXT,
    TEMPLATE_SALARY_TEXT,
    LakeVacancies,
)
from talentscope.ingestion.pipeline import retire_unlisted_records, run_connector
from talentscope.ingestion.records import SourceJob, SourceUnavailable
from talentscope.lake.layout import Lake
from talentscope.lake.silver import build_silver
from talentscope.models import IngestionRun, Job, Source
from talentscope.vocab import PermissionStatus, RunStatus

from ..unit.test_lake_pipeline import _capture, _posting, _write_bronze, reviewed_fixture_sites  # noqa: F401
from .conftest import make_source


def _lake(tmp_path: Path) -> Lake:
    lake = Lake(tmp_path / "lake")
    lake.ensure()
    rows = [
        _capture(
            "https://lokera.id/1",
            "lokera.id",
            _posting("Admin Gudang", "PT Maju", "Bandung", "2026-09-01"),
        ),
        _capture(
            "https://lokerb.id/9",
            "lokerb.id",
            _posting("Admin Gudang", "PT Maju", "Bandung", "2026-09-03"),
        ),
        _capture(
            "https://lokera.id/5",
            "lokera.id",
            _posting("Perawat", "RS Sehat", "Bogor", "2026-08-20", None),
        ),
    ]
    rows += [
        _capture(
            f"https://lokerd.id/{i}",
            "lokerd.id",
            _posting(
                f"Posisi {i} Bagian {chr(65 + i)}",
                f"Perusahaan {i}",
                "Medan",
                "2026-09-01",
                (2_500_000, 2_500_000),
            ),
        )
        for i in range(10)
    ]
    _write_bronze(lake, rows)
    build_silver(lake)
    return lake


def test_publish_one_job_per_canonical_vacancy(session: Session, tmp_path: Path) -> None:
    lake = _lake(tmp_path)
    source = make_source(
        session,
        "commoncrawl-jobposting",
        PermissionStatus.APPROVED_WITH_CONDITIONS,
        technical_method="manual_import",
        connector="lake_vacancies",
    )
    connector = LakeVacancies(lake.silver / "vacancies.parquet", "commoncrawl-jobposting")
    run = run_connector(session, source, connector)
    assert run.status == RunStatus.SUCCEEDED.value
    assert run.records_created == 12  # 13 pages -> 12 vacancies (one syndicated pair)

    gudang = session.scalar(select(Job).where(Job.title == "Admin Gudang"))
    assert gudang is not None
    assert gudang.source_url == "https://lokera.id/1"  # earliest member is the representative
    assert gudang.province == "Jawa Barat"
    assert (gudang.salary_monthly_min, gudang.salary_status) == (4_000_000, "DISCLOSED")
    assert gudang.last_seen_at.year == 2026 and gudang.published_at is not None
    assert gudang.description is None  # descriptions are never published

    perawat = session.scalar(select(Job).where(Job.title == "Perawat"))
    assert perawat is not None and perawat.salary_status == "NOT_DISCLOSED"

    template = session.scalars(select(Job).where(Job.company_name.like("Perusahaan %"))).all()
    assert {job.salary_status for job in template} == {"UNPARSEABLE"}
    assert {job.salary_text for job in template} == {TEMPLATE_SALARY_TEXT}

    again = run_connector(session, source, connector)
    assert (again.records_created, again.records_unchanged) == (0, 12)
    assert session.scalar(select(func.count()).select_from(Job)) == 12


def test_republish_retires_vacancies_a_rebuild_no_longer_contains(
    session: Session, tmp_path: Path
) -> None:
    source = make_source(
        session,
        "commoncrawl-jobposting",
        PermissionStatus.APPROVED_WITH_CONDITIONS,
        technical_method="manual_import",
        connector="lake_vacancies",
    )
    first = LakeVacancies(_lake(tmp_path / "a").silver / "vacancies.parquet", source.id)
    run_connector(session, source, first)

    # A later build where the two nursing/warehouse vacancies are gone (e.g. merged or
    # from a newly excluded site): only the ten templated-salary vacancies remain.
    lake = Lake(tmp_path / "b" / "lake")
    lake.ensure()
    _write_bronze(
        lake,
        [
            _capture(
                f"https://lokerd.id/{i}",
                "lokerd.id",
                _posting(
                    f"Posisi {i} Bagian {chr(65 + i)}", f"Perusahaan {i}", "Medan", "2026-09-01"
                ),
            )
            for i in range(10)
        ],
    )
    build_silver(lake)
    second = LakeVacancies(lake.silver / "vacancies.parquet", source.id)
    run = run_connector(session, source, second)

    # A complete snapshot retires what it no longer contains within the same run.
    assert run.status == RunStatus.SUCCEEDED.value
    assert (run.details["retired_records"], run.details["retired_jobs"]) == (2, 2)
    assert session.scalar(select(func.count()).select_from(Job)) == 10
    assert session.scalar(select(Job).where(Job.title == "Perawat")) is None
    assert retire_unlisted_records(session, source, second.current_keys(), actor="test") == (0, 0)


def _lake_source(session: Session) -> Source:
    return make_source(
        session,
        "commoncrawl-jobposting",
        PermissionStatus.APPROVED_WITH_CONDITIONS,
        technical_method="manual_import",
        connector="lake_vacancies",
    )


class _BreaksMidway(LakeVacancies):
    """A rebuilt snapshot whose read fails after some vacancies were already yielded."""

    def __init__(self, path: Path, source_id: str, error: Exception) -> None:
        super().__init__(path, source_id)
        self.error = error

    def fetch(self) -> Iterator[SourceJob]:
        for number, job in enumerate(super().fetch()):
            if number == 3:
                raise self.error
            yield job


@pytest.mark.parametrize(
    "error", [SourceUnavailable("disk read failed"), RuntimeError("bug in the connector")]
)
def test_failed_snapshot_publish_leaves_the_previous_snapshot_untouched(
    session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    source = _lake_source(session)
    run_connector(
        session,
        source,
        LakeVacancies(_lake(tmp_path / "a").silver / "vacancies.parquet", source.id),
    )
    before = sorted(session.scalars(select(Job.title)))

    # A different build (new vacancies) whose publish breaks after three records. Even with
    # a commit after every record, nothing of it may become visible.
    lake = Lake(tmp_path / "b" / "lake")
    lake.ensure()
    _write_bronze(
        lake,
        [
            _capture(
                f"https://lokerz.id/{i}",
                "lokerz.id",
                _posting(f"Kurir {i}", f"PT Kirim {i}", "Depok", "2026-09-01"),
            )
            for i in range(6)
        ],
    )
    build_silver(lake)
    monkeypatch.setattr("talentscope.ingestion.pipeline.COMMIT_EVERY", 1)
    broken = _BreaksMidway(lake.silver / "vacancies.parquet", source.id, error)
    if isinstance(error, RuntimeError):
        with pytest.raises(RuntimeError):
            run_connector(session, source, broken)
        run = session.scalars(select(IngestionRun).order_by(IngestionRun.started_at.desc())).first()
    else:
        run = run_connector(session, source, broken)
    assert run is not None and run.status == RunStatus.FAILED.value
    assert sorted(session.scalars(select(Job.title))) == before


class _SnapshotWithInvalidRecord(LakeVacancies):
    def fetch(self) -> Iterator[SourceJob]:
        yield from super().fetch()
        yield SourceJob(source_key="no-title", source_key_kind="content_fingerprint", title=None)


def test_snapshot_with_rejected_records_publishes_nothing(session: Session, tmp_path: Path) -> None:
    source = _lake_source(session)
    connector = _SnapshotWithInvalidRecord(_lake(tmp_path).silver / "vacancies.parquet", source.id)
    run = run_connector(session, source, connector)
    assert run.status == RunStatus.FAILED.value
    assert (run.records_seen, run.records_rejected, run.details["rolled_back"]) == (13, 1, True)
    assert "nothing was published" in (run.message or "")
    assert session.scalar(select(func.count()).select_from(Job)) == 0


def test_template_deadlines_and_implausible_salaries_are_not_published_as_facts(
    session: Session, tmp_path: Path
) -> None:
    lake = Lake(tmp_path / "lake")
    lake.ensure()
    rows = []
    for i in range(20):  # a site whose every validThrough is one theme default
        posting = _posting(f"Operator {i}", f"PT Pabrik {i}", "Bekasi", "2026-08-01")
        posting["validThrough"] = "2026-08-23"
        rows.append(_capture(f"https://lokera.id/{i}", "lokera.id", posting))
    real = _posting("Perawat", "RS Sehat", "Bogor", "2026-08-20", None)
    real["validThrough"] = "2026-09-05"
    rows.append(_capture("https://lokerb.id/1", "lokerb.id", real))
    rows.append(
        _capture(
            "https://lokerb.id/2",
            "lokerb.id",
            _posting("Customer Relations", "PT Finansial", "Bekasi", "2026-09-01", (2, 897)),
        )
    )
    _write_bronze(lake, rows)
    build_silver(lake)
    source = _lake_source(session)
    run = run_connector(
        session, source, LakeVacancies(lake.silver / "vacancies.parquet", source.id)
    )
    assert run.status == RunStatus.SUCCEEDED.value

    template = session.scalar(select(Job).where(Job.title == "Operator 0"))
    assert template is not None and template.expires_at is None
    record = template.source_records[0]
    assert record.raw_fields["source_valid_through"] == "2026-08-23"
    assert record.raw_fields["valid_through_unreliable"] is True

    perawat = session.scalar(select(Job).where(Job.title == "Perawat"))
    assert perawat is not None and perawat.expires_at is not None
    # Open through the deadline day in Indonesia (23:59:59 WIB), not until 00:00 UTC.
    assert perawat.expires_at == datetime(2026, 9, 5, 16, 59, 59, tzinfo=timezone.utc)
    assert perawat.source_records[0].raw_fields["valid_through_unreliable"] is False

    low = session.scalar(select(Job).where(Job.title == "Customer Relations"))
    assert low is not None
    assert (low.salary_status, low.salary_monthly_min, low.salary_min) == (
        "UNPARSEABLE",
        None,
        None,
    )
    assert low.salary_text == IMPLAUSIBLE_SALARY_TEXT
