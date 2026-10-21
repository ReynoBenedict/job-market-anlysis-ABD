import json
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from talentscope.ingestion.connectors.base import Connector
from talentscope.ingestion.connectors.legacy_glints_csv import LegacyGlintsSnapshot
from talentscope.ingestion.pipeline import run_connector, run_source
from talentscope.ingestion.records import AccessDenied, SourceJob
from talentscope.models import AuditEvent, IngestionRun, Job, Source, SourceRecord
from talentscope.sources import LEGACY_SNAPSHOT_SOURCE_ID, set_paused, sync_registry
from talentscope.vocab import PermissionStatus, RunErrorCategory, RunStatus

from .conftest import FIXTURES, SNAPSHOT_OBSERVED_AT, make_source


def _legacy(path: Path = FIXTURES / "legacy_sample.csv") -> LegacyGlintsSnapshot:
    return LegacyGlintsSnapshot(path, SNAPSHOT_OBSERVED_AT)


def _count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


class ListConnector(Connector):
    """In-memory connector for exercising the pipeline without files or network."""

    name = "list"
    parser_version = "list/1"
    mode = "collect"

    def __init__(
        self,
        jobs: list[SourceJob],
        *,
        fail_after: int | None = None,
        observed: datetime = datetime(2026, 10, 1, tzinfo=timezone.utc),
    ) -> None:
        self.jobs, self.fail_after, self.observed = jobs, fail_after, observed

    def describe_input(self) -> str:
        return "in-memory"

    def observed_at(self) -> datetime:
        return self.observed

    def fetch(self) -> Iterator[SourceJob]:
        for index, job in enumerate(self.jobs):
            if self.fail_after is not None and index == self.fail_after:
                raise AccessDenied("source answered HTTP 403; stopping")
            yield job


def _job(
    key: str,
    title: str = "Data Engineer",
    company: str = "PT Contoh",
    location: str = "Bandung,Jawa Barat",
) -> SourceJob:
    return SourceJob(
        source_key=key,
        source_key_kind="source_id",
        title=title,
        company_name=company,
        location_text=location,
        raw_fields={"key": key, "title": title},
    )


def test_legacy_import_is_idempotent(session: Session) -> None:
    source = make_source(
        session, "legacy", PermissionStatus.APPROVED_WITH_CONDITIONS, connector="legacy_glints_csv"
    )

    first = run_connector(session, source, _legacy())
    assert first.status == RunStatus.PARTIAL.value  # the fixture has one row without a title
    assert (first.records_seen, first.records_created, first.records_rejected) == (5, 4, 1)
    assert first.details["rejection_samples"][0]["reason"] == "record has no job title"
    assert first.input_reference is not None and "sha256=" in first.input_reference

    second = run_connector(session, source, _legacy())
    assert (second.records_created, second.records_unchanged) == (0, 4)
    assert _count(session, Job) == 4
    assert _count(session, SourceRecord) == 4


def test_legacy_rows_are_normalized_honestly(session: Session) -> None:
    source = make_source(
        session, "legacy", PermissionStatus.APPROVED_WITH_CONDITIONS, connector="legacy_glints_csv"
    )
    run_connector(session, source, _legacy())
    jobs = {job.title: job for job in session.scalars(select(Job))}

    hidden = jobs["C++ Software Engineer"]
    assert hidden.salary_status == "NOT_DISCLOSED" and hidden.salary_min is None
    assert hidden.is_urgent and hidden.posted_age_days == 1
    assert hidden.source_tags == ["C++"] and hidden.hidden_tag_count == 2

    remote = jobs["UI/UX Designer Intern"]
    assert remote.work_arrangement == "REMOTE" and remote.source_tags == []
    assert (remote.salary_monthly_min, remote.salary_monthly_max) == (1_000_000, 1_500_000)
    assert remote.city == "Yogyakarta"

    assert jobs["Staff Admin Gudang"].work_arrangement == "HYBRID"
    assert all(job.source_url is None for job in jobs.values())  # the snapshot has no URLs
    assert all(job.last_seen_at == SNAPSHOT_OBSERVED_AT for job in jobs.values())


def test_missing_columns_fail_the_run_as_schema_change(session: Session, tmp_path: Path) -> None:
    broken = tmp_path / "broken.csv"
    broken.write_text("job_title,company_name\nData Engineer,PT Contoh\n", encoding="utf-8")
    source = make_source(
        session, "legacy", PermissionStatus.APPROVED_WITH_CONDITIONS, connector="legacy_glints_csv"
    )
    run = run_connector(session, source, _legacy(broken))
    assert run.status == RunStatus.FAILED.value
    assert run.error_category == RunErrorCategory.SCHEMA_CHANGED.value


@pytest.mark.parametrize(
    "status",
    [
        PermissionStatus.BLOCKED,
        PermissionStatus.NEEDS_REVIEW,
        PermissionStatus.REQUIRES_WRITTEN_PERMISSION,
    ],
)
def test_ineligible_source_is_refused_and_recorded(
    session: Session, status: PermissionStatus
) -> None:
    source = make_source(
        session,
        "blocked",
        status,
        technical_method="api",
        connector="lever",
        connector_config={"site": "x", "company_name": "X"},
    )
    run = run_source(session, source, client=None)
    assert run.status == RunStatus.REFUSED.value
    assert run.error_category == RunErrorCategory.POLICY_BLOCKED.value
    assert _count(session, Job) == 0


def test_paused_source_is_refused(session: Session) -> None:
    source = make_source(
        session, "legacy", PermissionStatus.APPROVED_WITH_CONDITIONS, connector="legacy_glints_csv"
    )
    set_paused(session, source, True, actor="tester", reason="maintenance")
    assert run_connector(session, source, _legacy()).status == RunStatus.REFUSED.value


def test_resume_of_ineligible_source_is_rejected(session: Session) -> None:
    source = make_source(session, "blocked", PermissionStatus.BLOCKED, is_paused=True)
    with pytest.raises(PermissionError):
        set_paused(session, source, False, actor="tester", reason="try")
    assert source.is_paused


def test_connector_failure_after_some_records_is_partial(session: Session) -> None:
    source = make_source(
        session, "api", PermissionStatus.APPROVED, technical_method="api", connector="list"
    )
    run = run_connector(
        session,
        source,
        ListConnector([_job("a"), _job("b", "QA Engineer"), _job("c")], fail_after=2),
    )
    assert run.status == RunStatus.PARTIAL.value
    assert run.error_category == RunErrorCategory.ACCESS_DENIED.value
    assert run.records_created == 2


def test_empty_result_is_success_but_marked(session: Session) -> None:
    source = make_source(
        session, "api", PermissionStatus.APPROVED, technical_method="api", connector="list"
    )
    run = run_connector(session, source, ListConnector([]))
    assert run.status == RunStatus.SUCCEEDED.value
    assert run.details["empty_result"] is True


def test_cross_source_exact_match_links_records(session: Session) -> None:
    a = make_source(
        session, "source-a", PermissionStatus.APPROVED, technical_method="api", connector="list"
    )
    b = make_source(
        session, "source-b", PermissionStatus.APPROVED, technical_method="api", connector="list"
    )
    run_connector(session, a, ListConnector([_job("a-1")]))
    run = run_connector(
        session, b, ListConnector([_job("b-77", title="DATA ENGINEER", company="pt contoh")])
    )
    assert run.cross_source_matches == 1
    assert _count(session, Job) == 1
    assert _count(session, SourceRecord) == 2
    record = session.scalar(select(SourceRecord).where(SourceRecord.source_id == "source-b"))
    assert record is not None and record.match_rule == "cross_source_fingerprint"


def test_same_source_similar_listings_stay_separate(session: Session) -> None:
    source = make_source(
        session, "api", PermissionStatus.APPROVED, technical_method="api", connector="list"
    )
    run_connector(
        session,
        source,
        ListConnector([_job("1"), _job("2"), _job("3", location="Surabaya,Jawa Timur")]),
    )
    assert _count(session, Job) == 3


def test_older_observation_does_not_move_last_seen_backwards(session: Session) -> None:
    source = make_source(
        session, "api", PermissionStatus.APPROVED, technical_method="api", connector="list"
    )
    newer = datetime(2026, 10, 10, tzinfo=timezone.utc)
    older = datetime(2026, 9, 1, tzinfo=timezone.utc)
    run_connector(session, source, ListConnector([_job("1")], observed=newer))
    run_connector(session, source, ListConnector([_job("1")], observed=older))
    job = session.scalar(select(Job))
    assert job is not None
    assert (job.first_seen_at, job.last_seen_at) == (older, newer)


def test_changed_content_updates_the_job(session: Session) -> None:
    source = make_source(
        session, "api", PermissionStatus.APPROVED, technical_method="api", connector="list"
    )
    run_connector(session, source, ListConnector([_job("1", title="Data Analyst")]))
    run = run_connector(session, source, ListConnector([_job("1", title="Senior Data Analyst")]))
    assert run.records_updated == 1
    job = session.scalar(select(Job))
    assert job is not None and job.title == "Senior Data Analyst"


def test_registry_sync_respects_newer_audited_decisions(session: Session, tmp_path: Path) -> None:
    matrix = tmp_path / "matrix.json"
    entry = {
        "slug": "kalibrr",
        "name": "Kalibrr",
        "canonical_domain": "kalibrr.com",
        "category": "general_board",
        "permission_status": "REQUIRES_WRITTEN_PERMISSION",
        "technical_method": "unknown",
        "terms_url": None,
        "robots_url": None,
        "api_docs_url": None,
        "reason": "needs permission",
        "attribution_requirements": None,
        "retention_constraints": None,
        "reviewed_at": "2026-10-17T05:00:00Z",
    }
    matrix.write_text(json.dumps([entry]), encoding="utf-8")
    assert sync_registry(session, matrix) == {"created": 3, "updated": 0}
    assert session.get(Source, LEGACY_SNAPSHOT_SOURCE_ID) is not None

    kalibrr = session.get(Source, "kalibrr")
    assert kalibrr is not None
    kalibrr.permission_status = PermissionStatus.APPROVED.value
    kalibrr.reviewed_at = datetime(2026, 11, 1, tzinfo=timezone.utc)  # a later, recorded decision
    sync_registry(session, matrix)
    assert kalibrr.permission_status == PermissionStatus.APPROVED.value
    assert _count(session, AuditEvent) >= 2


def test_runs_are_persisted_with_counts(session: Session) -> None:
    source = make_source(
        session, "legacy", PermissionStatus.APPROVED_WITH_CONDITIONS, connector="legacy_glints_csv"
    )
    run_connector(session, source, _legacy())
    run = session.scalar(select(IngestionRun))
    assert (
        run is not None and run.finished_at is not None and run.observed_at == SNAPSHOT_OBSERVED_AT
    )
