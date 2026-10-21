from datetime import datetime, timezone

import pytest

from talentscope.ingestion.records import SalaryConvention, SourceJob, StructuredSalary
from talentscope.normalization.job import (
    FLAG_INVALID_SOURCE_URL,
    FLAG_SALARY_PERIOD_ASSUMED,
    FLAG_TAGS_TRUNCATED,
    InvalidSourceJob,
    normalize_source_job,
    validated_url,
)
from talentscope.vocab import SalaryPeriod

OBSERVED = datetime(2026, 6, 12, tzinfo=timezone.utc)
GLINTS_CONVENTION = SalaryConvention(currency="IDR", period=SalaryPeriod.MONTH)


def _job(**overrides: object) -> SourceJob:
    fields: dict[str, object] = {
        "source_key": "k1",
        "source_key_kind": "content_fingerprint",
        "title": "Data Engineer",
        "company_name": "PT Contoh",
        "location_text": "Jakarta Selatan,DKI Jakarta",
        "salary_text": "Rp 8 jt-12 jt",
        "employment_type_text": "Penuh Waktu",
        "tags": ("Hybrid", "SQL", "+4"),
        "raw_fields": {"job_title": "Data Engineer"},
    }
    fields.update(overrides)
    return SourceJob(**fields)  # type: ignore[arg-type]


def test_full_record_normalization() -> None:
    values = normalize_source_job(
        _job(), observed_at=OBSERVED, salary_convention=GLINTS_CONVENTION
    ).values
    assert values["role_family"] == "DATA_ANALYTICS"
    assert values["province"] == "DKI Jakarta"
    assert values["work_arrangement"] == "HYBRID"
    assert values["source_tags"] == ["SQL"]
    assert values["hidden_tag_count"] == 4
    assert (values["salary_monthly_min"], values["salary_monthly_max"]) == (8_000_000, 12_000_000)
    assert values["salary_period_assumed"] is True
    assert {FLAG_SALARY_PERIOD_ASSUMED, FLAG_TAGS_TRUNCATED} <= set(values["quality_flags"])
    assert "data engineer" in values["search_text"] and "sql" in values["search_text"]


def test_hidden_salary_stores_no_amounts() -> None:
    values = normalize_source_job(
        _job(salary_text="Gaji Tidak Ditampilkan"),
        observed_at=OBSERVED,
        salary_convention=GLINTS_CONVENTION,
    ).values
    assert values["salary_status"] == "NOT_DISCLOSED"
    assert values["salary_min"] is None and values["salary_monthly_min"] is None
    assert values["salary_currency"] is None


@pytest.mark.parametrize("title", [None, "", "   ", "Not Specified"])
def test_record_without_title_is_rejected(title: object) -> None:
    with pytest.raises(InvalidSourceJob):
        normalize_source_job(_job(title=title), observed_at=OBSERVED)


def test_structured_salary_period_is_not_an_assumption() -> None:
    job = _job(
        salary_text=None,
        structured_salary=StructuredSalary(120_000_000, 180_000_000, "IDR", SalaryPeriod.YEAR),
    )
    values = normalize_source_job(job, observed_at=OBSERVED).values
    assert values["salary_period"] == "YEAR"
    assert values["salary_period_assumed"] is False
    assert (values["salary_monthly_min"], values["salary_monthly_max"]) == (10_000_000, 15_000_000)


def test_explicit_work_arrangement_overrides_tags() -> None:
    values = normalize_source_job(_job(work_arrangement_text="remote"), observed_at=OBSERVED).values
    assert values["work_arrangement"] == "REMOTE"


@pytest.mark.parametrize(
    ("url", "valid"),
    [
        ("https://jobs.lever.co/acme/123", True),
        ("http://example.co.id/karir?id=1", True),
        ("javascript:alert(1)", False),
        ("ftp://example.com/job", False),
        ("/relative/path", False),
        ("https://", False),
    ],
)
def test_source_url_validation(url: str, valid: bool) -> None:
    assert (validated_url(url) == url) is valid


def test_invalid_url_is_dropped_and_flagged() -> None:
    values = normalize_source_job(
        _job(source_url="javascript:alert(1)"), observed_at=OBSERVED
    ).values
    assert values["source_url"] is None
    assert FLAG_INVALID_SOURCE_URL in values["quality_flags"]


def test_fingerprint_ignores_case_and_punctuation() -> None:
    a = normalize_source_job(
        _job(title="Data Engineer", company_name="PT. Contoh"), observed_at=OBSERVED
    )
    b = normalize_source_job(
        _job(title="DATA ENGINEER", company_name="pt contoh"), observed_at=OBSERVED
    )
    assert a.fingerprint == b.fingerprint
