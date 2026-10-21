from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from talentscope.ingestion.connectors.legacy_glints_csv import LegacyGlintsSnapshot
from talentscope.ingestion.pipeline import run_connector
from talentscope.ingestion.records import SourceJob, StructuredSalary
from talentscope.vocab import PermissionStatus, SalaryPeriod

from .conftest import ADMIN_TOKEN, FIXTURES, SNAPSHOT_OBSERVED_AT, make_source
from .test_pipeline import ListConnector

API = "/api/v1"


@pytest.fixture
def seeded(session: Session) -> Iterator[None]:
    source = make_source(
        session,
        "legacy",
        PermissionStatus.APPROVED_WITH_CONDITIONS,
        name="Snapshot uji",
        connector="legacy_glints_csv",
        coverage_note="Sampel uji sintetis.",
    )
    make_source(session, "blocked-board", PermissionStatus.BLOCKED, category="general_board")
    run_connector(
        session, source, LegacyGlintsSnapshot(FIXTURES / "legacy_sample.csv", SNAPSHOT_OBSERVED_AT)
    )
    yield


def test_health(client: TestClient) -> None:
    response = client.get(f"{API}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "x-request-id" in response.headers


def test_job_search_returns_real_records_with_labels(client: TestClient, seeded: None) -> None:
    body = client.get(f"{API}/jobs").json()
    assert body["total"] == 4 and body["total_pages"] == 1
    job = next(item for item in body["items"] if item["title"] == "Data Engineer")
    assert job["role_family"] == {"code": "DATA_ANALYTICS", "label": "Data & Analitik"}
    assert job["salary"]["period_assumed"] is True
    assert job["freshness"]["code"] == "NOT_SEEN_RECENTLY"  # observed in June, window is 30 days
    assert job["source"]["name"] == "Snapshot uji"
    assert job["source_url"] is None


@pytest.mark.parametrize(
    ("query", "titles"),
    [
        ("q=engineer", {"Data Engineer", "C++ Software Engineer"}),
        ("q=c%2B%2B", {"C++ Software Engineer"}),
        ("q=data%20jakarta", {"Data Engineer"}),
        ("q=100%25", set()),  # LIKE wildcards are escaped, not interpreted
        ("employment_type=INTERNSHIP", {"UI/UX Designer Intern"}),
        (
            "work_arrangement=REMOTE&work_arrangement=HYBRID",
            {"UI/UX Designer Intern", "Staff Admin Gudang"},
        ),
        ("province=Bali", {"C++ Software Engineer"}),
        ("salary_disclosed=false", {"C++ Software Engineer"}),
        ("salary_min=5000000", {"Data Engineer"}),
        ("salary_max=2000000", {"UI/UX Designer Intern"}),
        ("freshness=POTENTIALLY_ACTIVE", set()),
    ],
)
def test_filters(client: TestClient, seeded: None, query: str, titles: set[str]) -> None:
    body = client.get(f"{API}/jobs?{query}").json()
    assert {item["title"] for item in body["items"]} == titles
    assert body["total"] == len(titles)


def test_pagination_is_bounded_and_stable(client: TestClient, seeded: None) -> None:
    first = client.get(f"{API}/jobs?page_size=2&page=1&sort=title").json()
    second = client.get(f"{API}/jobs?page_size=2&page=2&sort=title").json()
    titles = [i["title"] for i in first["items"] + second["items"]]
    assert titles == sorted(titles, key=str.casefold)
    assert len(set(titles)) == 4
    assert client.get(f"{API}/jobs?page_size=51").status_code == 422


def test_salary_sort_puts_unknown_salaries_last(client: TestClient, seeded: None) -> None:
    items = client.get(f"{API}/jobs?sort=salary_desc").json()["items"]
    assert items[0]["title"] == "Data Engineer"
    assert items[-1]["salary"]["status"]["code"] == "NOT_DISCLOSED"


@pytest.mark.parametrize(
    "query",
    [
        "role_family=NOT_A_FAMILY",
        "salary_min=-1",
        "salary_min=9&salary_max=1",
        "sort=random",
        f"q={'x' * 101}",
    ],
)
def test_invalid_requests_use_error_envelope(client: TestClient, query: str) -> None:
    response = client.get(f"{API}/jobs?{query}")
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_request" and error["details"]


def test_job_detail_and_missing_job(client: TestClient, seeded: None) -> None:
    job_id = client.get(f"{API}/jobs?q=data").json()["items"][0]["id"]
    detail = client.get(f"{API}/jobs/{job_id}").json()
    assert detail["source_records"][0]["source_key_kind"] == "content_fingerprint"
    assert detail["description"] is None
    missing = client.get(f"{API}/jobs/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "job_not_found"
    assert client.get(f"{API}/jobs/not-a-uuid").status_code == 422


def test_market_overview_counts_and_scope(client: TestClient, seeded: None) -> None:
    body = client.get(f"{API}/market/overview").json()
    assert (body["total_jobs"], body["salary_disclosed"], body["provinces"]) == (4, 3, 4)
    assert body["scope"]["is_historical"] is True
    assert body["scope"]["coverage_notes"] == ["Sampel uji sintetis."]


def test_breakdown_denominator_and_limit(client: TestClient, seeded: None) -> None:
    body = client.get(f"{API}/market/breakdown/employment_type?limit=2").json()
    assert body["total"] == 4 and body["distinct_values"] == 4
    assert sum(row["count"] for row in body["rows"]) + body["other_count"] == 4
    assert body["rows"][0]["label"] in {"Penuh waktu", "Kontrak", "Paruh waktu", "Magang"}


def test_salary_overview_withholds_statistics_below_minimum_sample(
    client: TestClient, seeded: None
) -> None:
    body = client.get(f"{API}/salaries/overview").json()
    assert body["eligible"] == 3
    assert body["period_assumed"] == 3
    assert body["min_records_for_statistics"] == 5
    assert body["percentiles"] is None and body["median_min"] is None
    assert sum(b["count"] for b in body["histogram"]) == 3


def test_salary_percentiles_use_monthly_midpoints(client: TestClient, session: Session) -> None:
    source = make_source(
        session, "api", PermissionStatus.APPROVED, technical_method="api", connector="list"
    )
    monthly = [(4, 6), (6, 8), (8, 12), (10, 10), (2, 4)]  # millions; midpoints 5, 7, 10, 10, 3
    jobs = [
        SourceJob(
            source_key=f"m{i}",
            source_key_kind="source_id",
            title=f"Analyst {i}",
            structured_salary=StructuredSalary(
                lo * 1_000_000, hi * 1_000_000, "IDR", SalaryPeriod.MONTH
            ),
        )
        for i, (lo, hi) in enumerate(monthly)
    ]
    # A yearly salary counts after conversion (120-144 jt/year -> 10-12 jt/month, midpoint 11).
    jobs.append(
        SourceJob(
            source_key="y",
            source_key_kind="source_id",
            title="Analyst yearly",
            structured_salary=StructuredSalary(120_000_000, 144_000_000, "IDR", SalaryPeriod.YEAR),
        )
    )
    # Hourly and foreign-currency pay are not comparable and must be excluded.
    jobs.append(
        SourceJob(
            source_key="h",
            source_key_kind="source_id",
            title="Analyst hourly",
            structured_salary=StructuredSalary(50_000, 80_000, "IDR", SalaryPeriod.HOUR),
        )
    )
    jobs.append(
        SourceJob(
            source_key="u",
            source_key_kind="source_id",
            title="Analyst usd",
            structured_salary=StructuredSalary(3_000, 4_000, "USD", SalaryPeriod.MONTH),
        )
    )
    run_connector(session, source, ListConnector(jobs))

    body = client.get(f"{API}/salaries/overview").json()
    assert body["eligible"] == 6
    assert body["period_assumed"] == 0
    # Sorted midpoints 3, 5, 7, 10, 10, 11 (millions): median = (7 + 10) / 2.
    assert body["percentiles"]["p50"] == pytest.approx(8_500_000)


def test_salary_statistics_withheld_for_small_groups(client: TestClient, seeded: None) -> None:
    body = client.get(f"{API}/salaries/compare?by=province").json()
    assert all(group["median"] is None for group in body["groups"])  # every group has n < 5
    assert all(group["small_sample"] for group in body["groups"])
    assert client.get(f"{API}/salaries/compare?by=title").status_code == 422


def test_source_tags_report_truncation(client: TestClient, seeded: None) -> None:
    body = client.get(f"{API}/skills/source-tags").json()
    assert body["jobs_with_hidden_tags"] == 4
    assert {t["value"] for t in body["top_tags"]} == {"SQL", "C++"}


def test_sources_coverage_lists_blocked_sources(client: TestClient, seeded: None) -> None:
    sources = {s["id"]: s for s in client.get(f"{API}/sources/coverage").json()}
    assert sources["legacy"]["job_count"] == 4
    assert sources["blocked-board"]["permission_status"]["code"] == "BLOCKED"
    assert sources["blocked-board"]["job_count"] == 0


def test_filter_options_reflect_data(client: TestClient, seeded: None) -> None:
    body = client.get(f"{API}/filters").json()
    assert body["total"] == 4
    assert {o["value"] for o in body["province"]} == {
        "DKI Jakarta",
        "Bali",
        "Jawa Barat",
        "DI Yogyakarta",
    }
    assert body["salary_monthly_range"] == [1_000_000, 12_000_000]


def test_admin_requires_token(client: TestClient, seeded: None) -> None:
    assert client.get(f"{API}/admin/sources").status_code == 401
    wrong = client.get(f"{API}/admin/sources", headers={"Authorization": "Bearer nope"})
    assert wrong.status_code == 401


def test_admin_cannot_resume_blocked_source(client: TestClient, seeded: None) -> None:
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    response = client.post(
        f"{API}/admin/sources/blocked-board/resume", json={"reason": "please"}, headers=headers
    )
    assert response.status_code == 409
    paused = client.post(
        f"{API}/admin/sources/legacy/pause", json={"reason": "maintenance"}, headers=headers
    )
    assert paused.status_code == 200 and paused.json()["is_paused"] is True
    events = client.get(f"{API}/admin/audit-events", headers=headers).json()
    assert events["items"][0]["action"] == "source.paused"


def test_admin_runs_and_quality(client: TestClient, seeded: None) -> None:
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    runs = client.get(f"{API}/admin/ingestion-runs", headers=headers).json()
    assert runs["total"] == 1 and runs["items"][0]["records_rejected"] == 1
    quality = client.get(f"{API}/admin/data-quality", headers=headers).json()
    assert quality["missing"]["source_url"] == 4
    assert quality["flags"]["TAGS_TRUNCATED"] == 4


def test_admin_disabled_without_token(session: Session) -> None:
    from talentscope.api.app import create_app
    from talentscope.api.deps import get_session
    from talentscope.config import Settings, get_settings

    from .conftest import TEST_DATABASE_URL

    settings = Settings(database_url=TEST_DATABASE_URL, admin_api_token=None)
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        response = client.get(f"{API}/admin/sources", headers={"Authorization": "Bearer anything"})
    assert response.status_code == 503
