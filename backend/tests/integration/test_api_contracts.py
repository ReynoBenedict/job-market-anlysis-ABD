"""Contract tests for the API audit: one salary-eligibility rule everywhere, publisher-site
counts, input hardening, and lifecycle boundaries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session

from talentscope.analytics.filters import JobFilters, apply_filters, freshness_of
from talentscope.analytics.salary_rule import comparable_salary, is_comparable
from talentscope.api.app import create_app
from talentscope.api.deps import get_session
from talentscope.config import Settings, get_settings
from talentscope.ingestion.pipeline import run_connector
from talentscope.ingestion.records import SourceJob
from talentscope.models import Job, Source
from talentscope.vocab import Freshness, PermissionStatus

from .conftest import ADMIN_TOKEN, TEST_DATABASE_URL, make_source
from .test_pipeline import ListConnector

API = "/api/v1"
M = 1_000_000


def _seed(session: Session, rows: dict[str, dict[str, Any]]) -> None:
    """Ingest one job per title, then set the given columns directly, so each test
    controls exactly the stored values the API reads."""
    source = make_source(
        session, "api", PermissionStatus.APPROVED, technical_method="api", connector="list"
    )
    jobs = [
        SourceJob(source_key=f"k{i}", source_key_kind="source_id", title=title)
        for i, title in enumerate(rows)
    ]
    run_connector(session, source, ListConnector(jobs))
    for title, values in rows.items():
        if values:
            session.execute(update(Job).where(Job.title == title).values(**values))
    session.flush()
    session.expire_all()


def _salary(lo: int, hi: int, currency: str = "IDR", **extra: Any) -> dict[str, Any]:
    return {
        "salary_status": "DISCLOSED",
        "salary_currency": currency,
        "salary_period": "MONTH",
        "salary_min": lo,
        "salary_max": hi,
        "salary_monthly_min": extra.pop("salary_monthly_min", lo),
        "salary_monthly_max": extra.pop("salary_monthly_max", hi),
        **extra,
    }


SALARY_ROWS: dict[str, dict[str, Any]] = {
    "Analis A": _salary(3 * M, 5 * M),  # midpoint 4 jt
    "Analis B": _salary(4 * M, 6 * M),  # 5 jt
    "Analis C": _salary(5 * M, 7 * M),  # 6 jt
    "Analis D": _salary(6 * M, 8 * M),  # 7 jt
    "Analis E": _salary(8 * M, 12 * M),  # 10 jt
    "Magang Tepat Batas": _salary(500_000, 500_000),  # midpoint exactly Rp500 rb: kept
    "Direktur Mahal": _salary(90 * M, 140 * M, quality_flags=["SALARY_HIGH_OUTLIER"]),
    # Not comparable:
    "Customer Relations Rusak": _salary(
        2, 897, quality_flags=["SALARY_LOW_OUTLIER", "SALARY_WIDE_RANGE"]
    ),
    "Kasir Hampir Batas": _salary(499_999, 500_000),  # midpoint 499,999.5
    # salary_min/max are ordered by a CHECK constraint; the monthly columns are not.
    "Rentang Terbalik": _salary(3 * M, 9 * M, salary_monthly_min=9 * M, salary_monthly_max=3 * M),
    "Engineer USD": _salary(3_000, 4_000, currency="USD"),
    "Staf Tanpa Gaji": {},  # ingested as NOT_DISCLOSED/UNPARSEABLE
}
COMPARABLE = {
    "Analis A",
    "Analis B",
    "Analis C",
    "Analis D",
    "Analis E",
    "Magang Tepat Batas",
    "Direktur Mahal",
}


@pytest.fixture
def salaries(session: Session) -> None:
    _seed(session, SALARY_ROWS)


def test_salary_overview_uses_only_comparable_salaries(client: TestClient, salaries: None) -> None:
    body = client.get(f"{API}/salaries/overview").json()
    assert body["total_jobs"] == len(SALARY_ROWS)
    assert body["eligible"] == len(COMPARABLE)
    assert body["eligible_share"] == pytest.approx(len(COMPARABLE) / len(SALARY_ROWS))
    # Reversed range, midpoint below Rp500 rb, and the "Rp2–897" record; USD is not IDR.
    assert body["excluded_implausible"] == 3
    assert body["min_monthly_midpoint"] == 500_000
    # Midpoints 0.5, 4, 5, 6, 7, 10, 115 jt.
    assert body["percentiles"]["p50"] == pytest.approx(6 * M)
    assert body["median_min"] == pytest.approx(5 * M)  # lower bounds 0.5, 3, 4, 5, 6, 8, 90
    assert body["median_max"] == pytest.approx(7 * M)  # upper bounds 0.5, 5, 6, 7, 8, 12, 140
    assert sum(b["count"] for b in body["histogram"]) == len(COMPARABLE)
    assert body["histogram"][0]["count"] == 1  # only the Rp500 rb record, not "Rp2–897"
    assert body["flag_counts"] == {
        "SALARY_WIDE_RANGE": 0,
        "SALARY_HIGH_OUTLIER": 1,
        "SALARY_LOW_OUTLIER": 0,
    }


def test_salary_compare_counts_same_records(client: TestClient, salaries: None) -> None:
    groups = client.get(f"{API}/salaries/compare?by=source").json()["groups"]
    assert [(g["n"], g["jobs_in_group"]) for g in groups] == [(len(COMPARABLE), len(SALARY_ROWS))]
    assert groups[0]["median"] == pytest.approx(6 * M)


@pytest.mark.parametrize(
    ("query", "titles"),
    [
        # Before the shared rule, "Rp2–897", the 499,999.5 midpoint, and USD 3,000 matched.
        ("salary_max=600000", {"Magang Tepat Batas"}),
        ("salary_min=100000000", {"Direktur Mahal"}),
        (
            "salary_min=7000000&salary_max=9000000",
            {"Analis C", "Analis D", "Analis E"},
        ),
    ],
)
def test_salary_filters_apply_the_same_rule(
    client: TestClient, salaries: None, query: str, titles: set[str]
) -> None:
    body = client.get(f"{API}/jobs?{query}&page_size=50").json()
    assert {item["title"] for item in body["items"]} == titles
    overview = client.get(f"{API}/salaries/overview?{query}").json()
    assert overview["eligible"] == overview["total_jobs"] == len(titles)


def test_salary_sort_and_range_ignore_non_comparable(client: TestClient, salaries: None) -> None:
    items = client.get(f"{API}/jobs?sort=salary_desc&page_size=50").json()["items"]
    assert items[0]["title"] == "Direktur Mahal"
    assert {i["title"] for i in items[: len(COMPARABLE)]} == COMPARABLE
    assert all(i["salary"]["comparable"] is (i["title"] in COMPARABLE) for i in items)
    filters = client.get(f"{API}/filters").json()
    assert filters["salary_monthly_range"] == [500_000, 140 * M]


def test_sql_and_python_salary_rules_agree(session: Session, salaries: None) -> None:
    rows = session.execute(
        select(
            Job.title,
            comparable_salary(Job),
            Job.salary_status,
            Job.salary_currency,
            Job.salary_monthly_min,
            Job.salary_monthly_max,
        )
    ).all()
    assert len(rows) == len(SALARY_ROWS)
    for title, in_sql, status, currency, lo, hi in rows:
        assert bool(in_sql) is is_comparable(status, currency, lo, hi) is (title in COMPARABLE)


def test_publisher_sites_count_distinct_hosts(client: TestClient, session: Session) -> None:
    _seed(
        session,
        {
            "Situs A1": {"source_url": "https://www.situs-a.id/loker/1", "province": "Bali"},
            "Situs A2": {"source_url": "http://SITUS-A.id/loker/2?x=1"},
            "Situs B": {"source_url": "https://user@situs-b.co.id:8443/a"},
            "Situs C": {"source_url": "https://situs-c.id"},
            "Tanpa URL": {"source_url": None},
        },
    )
    overview = client.get(f"{API}/market/overview").json()
    assert overview["publisher_sites"] == overview["scope"]["publisher_sites"] == 3
    assert len(overview["scope"]["sources"]) == 1  # one ingestion source, three sites
    bali = client.get(f"{API}/market/overview?province=Bali").json()
    assert bali["publisher_sites"] == bali["scope"]["publisher_sites"] == 1
    salary_scope = client.get(f"{API}/salaries/overview").json()["scope"]
    assert salary_scope["publisher_sites"] == 3


def test_only_http_source_urls_are_returned(client: TestClient, session: Session) -> None:
    _seed(session, {"Lowongan Aneh": {"source_url": "javascript:alert(1)"}})
    item = client.get(f"{API}/jobs").json()["items"][0]
    assert item["source_url"] is None
    session.execute(update(Job).values(source_url="HTTPS://situs.id/a"))
    detail = client.get(f"{API}/jobs/{item['id']}").json()
    assert detail["source_url"] == "HTTPS://situs.id/a"


@pytest.mark.parametrize(
    ("query", "field"),
    [
        ("q=a%00b", "q"),
        ("province=a%00b", "province"),
        ("city=%00", "city"),
        ("source=x%00", "source"),
        (f"city={'x' * 201}", "city"),
        ("salary_min=99999999999", "salary_min"),
        ("salary_min=9&salary_max=1", None),  # cross-field rule names no single field
    ],
)
def test_invalid_filter_values_are_422_with_field(
    client: TestClient, query: str, field: str | None
) -> None:
    for path in ("jobs", "market/overview", "salaries/overview"):
        response = client.get(f"{API}/{path}?{query}")
        assert response.status_code == 422, path
        error = response.json()["error"]
        assert error["code"] == "invalid_request"
        assert [d["field"] for d in error["details"]] == [field]


def test_query_edge_cases_are_safe(client: TestClient, session: Session) -> None:
    _seed(session, {"Sun_up Barista": {}, "Barista 100% Kopi": {}, "Kasir 'Toko'": {}})
    cases = {
        "q=_": {"Sun_up Barista"},
        "q=%25": {"Barista 100% Kopi"},
        "q=%5C": set(),
        "q=%27toko%27": {"Kasir 'Toko'"},
        "q=caf%C3%A9%20%F0%9F%98%80": set(),
        "q=%20%20": {"Sun_up Barista", "Barista 100% Kopi", "Kasir 'Toko'"},
        "q=barista&unknown_param=1": {"Sun_up Barista", "Barista 100% Kopi"},
    }
    for query, titles in cases.items():
        body = client.get(f"{API}/jobs?{query}").json()
        assert {i["title"] for i in body["items"]} == titles, query
    beyond = client.get(f"{API}/jobs?page=50").json()
    assert beyond["items"] == [] and beyond["total"] == 3 and beyond["total_pages"] == 1


def test_admin_source_id_is_validated(client: TestClient) -> None:
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    bad = client.post(
        f"{API}/admin/sources/bad%00id/pause", json={"reason": "maintenance"}, headers=headers
    )
    assert bad.status_code == 422
    missing = client.post(
        f"{API}/admin/sources/no-such-source/pause", json={"reason": "maintenance"}, headers=headers
    )
    assert missing.status_code == 404
    runs = client.get(f"{API}/admin/ingestion-runs?source_id=%00", headers=headers)
    assert runs.status_code == 422
    assert client.get(f"{API}/admin/audit-events?page=10001", headers=headers).status_code == 422


def test_request_id_is_reused_only_when_plain(client: TestClient) -> None:
    kept = client.get(f"{API}/health", headers={"X-Request-ID": "abc-123.x_y"})
    assert kept.headers["x-request-id"] == "abc-123.x_y"
    replaced = client.get(f"{API}/health", headers={"X-Request-ID": "a b <script>"})
    assert replaced.headers["x-request-id"] != "a b <script>"
    assert len(replaced.headers["x-request-id"]) == 32


def test_health_reports_unreachable_database(settings: Settings) -> None:
    # Port 1 on the loopback interface refuses connections immediately.
    engine = create_engine("postgresql+psycopg://x:x@127.0.0.1:1/x?connect_timeout=2")
    broken = Session(bind=engine)
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: broken
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            response = client.get(f"{API}/health")
    finally:
        broken.close()
        engine.dispose()
    assert response.status_code == 503
    body = response.json()["error"]
    assert body["code"] == "database_unavailable" and "127.0.0.1" not in body["message"]


# --- Lifecycle (freshness) boundaries ---------------------------------------------------

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
WINDOW = 30
TICK = timedelta(microseconds=1)
LIFECYCLE_CASES: dict[str, tuple[datetime, datetime | None, Freshness]] = {
    # title: (last_seen_at, expires_at, expected)
    "Batas jendela": (NOW - timedelta(days=WINDOW), None, Freshness.POTENTIALLY_ACTIVE),
    "Lewat jendela": (NOW - timedelta(days=WINDOW) - TICK, None, Freshness.NOT_SEEN_RECENTLY),
    "Kedaluwarsa tepat sekarang": (NOW, NOW, Freshness.POTENTIALLY_ACTIVE),
    "Kedaluwarsa sedetik lalu": (NOW, NOW - TICK, Freshness.EXPIRED_BY_SOURCE),
    # A future deadline is no evidence the listing is live: old sightings stay history.
    "Tenggat masa depan, lama": (
        NOW - timedelta(days=200),
        NOW + timedelta(days=60),
        Freshness.NOT_SEEN_RECENTLY,
    ),
    "Tanpa tenggat, lama": (NOW - timedelta(days=200), None, Freshness.NOT_SEEN_RECENTLY),
    "Kedaluwarsa walau baru terlihat": (
        NOW - timedelta(days=1),
        NOW - timedelta(days=2),
        Freshness.EXPIRED_BY_SOURCE,
    ),
}


@pytest.mark.parametrize("title", LIFECYCLE_CASES)
def test_freshness_of_boundaries(title: str) -> None:
    last_seen, expires, expected = LIFECYCLE_CASES[title]
    assert freshness_of(last_seen, expires, window_days=WINDOW, now=NOW) is expected


def test_freshness_clause_matches_freshness_of(session: Session) -> None:
    _seed(
        session,
        {
            title: {"last_seen_at": last_seen, "expires_at": expires}
            for title, (last_seen, expires, _) in LIFECYCLE_CASES.items()
        },
    )
    for status in Freshness:
        stmt = apply_filters(
            select(Job.title), JobFilters(freshness=[status]), freshness_window_days=WINDOW, now=NOW
        )
        expected = {t for t, (_, _, label) in LIFECYCLE_CASES.items() if label is status}
        assert set(session.scalars(stmt)) == expected, status
    # The three labels partition every job: none is counted twice or dropped.
    every = apply_filters(
        select(Job.title),
        JobFilters(freshness=list(Freshness)),
        freshness_window_days=WINDOW,
        now=NOW,
    )
    assert len(session.scalars(every).all()) == len(LIFECYCLE_CASES)


def test_settings_fixture_is_test_database(settings: Settings) -> None:
    # Guard: these tests write rows and must never point at the real database.
    assert settings.database_url == TEST_DATABASE_URL
    assert not TEST_DATABASE_URL.endswith("/talentscope")


def test_source_public_label_and_published_range(client: TestClient, session: Session) -> None:
    _seed(
        session,
        {
            "Lama": {"published_at": datetime(2025, 3, 1, tzinfo=timezone.utc)},
            "Baru": {"published_at": datetime(2026, 9, 1, tzinfo=timezone.utc)},
            "Tanpa tanggal": {},
        },
    )
    session.execute(
        update(Source)
        .where(Source.id == "api")
        .values(
            public_label="Boleh dipakai dengan syarat", public_condition="Hak tetap milik situs."
        )
    )
    session.expire_all()
    scope = client.get(f"{API}/market/overview").json()["scope"]
    assert scope["published_from"].startswith("2025-03-01")
    assert scope["published_to"].startswith("2026-09-01")
    assert scope["sources"][0]["public_label"] == "Boleh dipakai dengan syarat"
    assert scope["sources"][0]["public_condition"] == "Hak tetap milik situs."
    coverage = {s["id"]: s for s in client.get(f"{API}/sources/coverage").json()}
    assert coverage["api"]["public_label"] == "Boleh dipakai dengan syarat"
    assert coverage["api"]["permission_status"]["label"] == "Diizinkan (izin/lisensi tercatat)"
    empty = client.get(f"{API}/market/overview?q=tidakada").json()["scope"]
    assert empty["published_from"] is None and empty["published_to"] is None


def test_unset_public_label_is_null(client: TestClient, session: Session) -> None:
    make_source(session, "plain", PermissionStatus.APPROVED_WITH_CONDITIONS)
    coverage = {s["id"]: s for s in client.get(f"{API}/sources/coverage").json()}
    assert coverage["plain"]["public_label"] is None
    assert coverage["plain"]["public_condition"] is None
    assert coverage["plain"]["permission_status"]["label"] == "Boleh dipakai dengan syarat"


# --- Exact tag filter -------------------------------------------------------------------


def test_tag_filter_matches_exact_card_tags(client: TestClient, session: Session) -> None:
    _seed(
        session,
        {
            "Staf Akuntansi": {"source_tags": ["Accounting", "Microsoft Excel"]},
            "Kasir Toko": {"source_tags": ["Customer Service"]},
            # Mentions the word in its title but does not carry the tag: not a tag match.
            "Accounting Manager": {"source_tags": []},
        },
    )
    by_tag = client.get(f"{API}/jobs", params={"tag": "Accounting"}).json()
    assert [job["title"] for job in by_tag["items"]] == ["Staf Akuntansi"]

    either = client.get(f"{API}/jobs", params=[("tag", "Accounting"), ("tag", "Customer Service")])
    assert either.json()["total"] == 2
    # The same filter drives analytics, so counts on the skills page and search agree.
    assert (
        client.get(f"{API}/market/overview", params={"tag": "Customer Service"}).json()[
            "total_jobs"
        ]
        == 1
    )
    assert client.get(f"{API}/jobs", params={"tag": "x" * 201}).status_code == 422
