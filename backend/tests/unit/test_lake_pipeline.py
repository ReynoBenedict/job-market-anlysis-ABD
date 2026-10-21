"""Bronze → silver → gold on a temporary lake built from synthetic fixtures (never real data)."""

import gzip
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import duckdb
import httpx
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from talentscope.lake.commoncrawl.collect import CAPTURE_SCHEMA, MIN_DOMAIN_TRIALS, collect_crawl
from talentscope.lake.commoncrawl.warc import ArchiveFetcher
from talentscope.lake.domain_reviews import DOMAIN_REVIEWS, DomainReview, ReviewStatus
from talentscope.lake.gold import build_gold
from talentscope.lake.layout import Lake
from talentscope.lake.silver import build_silver, parse_bronze

CRAWL = "CC-MAIN-2026-39"
FIXTURE_SITES = (
    "lokera.id",
    "lokerb.id",
    "lokerc.id",
    "lokerd.id",
    "lokere.id",
    "lokerz.id",
    "jobs-site.id",
    "news.id",
)


@pytest.fixture(autouse=True)
def reviewed_fixture_sites(monkeypatch: pytest.MonkeyPatch) -> None:
    """Synthetic sites count as reviewed (silver only uses reviewed archive sites)."""
    for site in FIXTURE_SITES:
        monkeypatch.setitem(DOMAIN_REVIEWS, site, DomainReview(ReviewStatus.NO_STATEMENT))


LATER_CRAWL = "CC-MAIN-2026-43"


def _posting(
    title: str,
    org: str,
    city: str,
    posted: str,
    salary: tuple[int, int] | None = (4_000_000, 5_000_000),
) -> dict:
    posting = {
        "@type": "JobPosting",
        "title": title,
        "hiringOrganization": {"name": org} if org else None,
        "jobLocation": {"address": {"addressLocality": city, "addressCountry": "ID"}},
        "datePosted": posted,
        "description": "Deskripsi sintetis untuk pengujian. Menguasai Microsoft Excel. " + "x" * 80,
    }
    if salary:
        posting["baseSalary"] = {
            "currency": "IDR",
            "value": {"minValue": salary[0], "maxValue": salary[1], "unitText": "MONTH"},
        }
    return posting


def _capture(
    url: str, domain: str, posting: dict, *, digest: str | None = None, crawl: str = CRAWL
) -> dict:
    captured = datetime(2026, 9, 10, tzinfo=timezone.utc)
    return {
        "crawl": crawl,
        "url": url,
        "domain": domain,
        "index_fetch_time": captured,
        "content_digest": digest or f"sha1:{abs(hash(url))}",
        "warc_filename": f"crawl-data/{crawl}/x.warc.gz",
        "warc_record_offset": abs(hash(url)) % 10_000_000,
        "warc_record_length": 100,
        "captured_at": captured,
        "http_status": 200,
        "fetch_result": "ok",
        "jobposting_count": 1,
        "malformed_jsonld": 0,
        "postings_json": json.dumps([posting]),
        "fetched_at": captured,
        "connector_version": "test",
    }


def _write_bronze(lake: Lake, rows: list[dict], crawl: str = CRAWL, name: str = "batch-1") -> None:
    target = lake.cc_captures_dir(crawl)
    target.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows, schema=CAPTURE_SCHEMA), target / f"{name}.parquet")


@pytest.fixture
def lake(tmp_path: Path) -> Lake:
    lake = Lake(tmp_path / "lake")
    lake.ensure()
    rows = [
        # Same opening syndicated to two sites, and reposted on the first site.
        _capture(
            "https://lokera.id/1",
            "lokera.id",
            _posting("Lowongan Admin Gudang PT Maju Bandung", "PT Maju", "Bandung", "2026-09-01"),
        ),
        _capture(
            "https://lokerb.id/9",
            "lokerb.id",
            _posting("Admin Gudang", "PT Maju", "Bandung", "2026-09-03"),
        ),
        _capture(
            "https://lokera.id/2",
            "lokera.id",
            _posting("Admin Gudang (Urgent)", "PT Maju", "Bandung", "2026-09-05"),
        ),
        # Same title much later: a new opening.
        _capture(
            "https://lokera.id/3",
            "lokera.id",
            _posting("Admin Gudang", "PT Maju", "Bandung", "2026-03-01"),
        ),
        # Same role in another city: a different vacancy.
        _capture(
            "https://lokera.id/4",
            "lokera.id",
            _posting("Admin Gudang", "PT Maju", "Surabaya", "2026-09-01"),
        ),
        # Near-identical title in the same place: merged by fuzzy matching.
        _capture(
            "https://lokerb.id/10",
            "lokerb.id",
            _posting("Staff Akuntansi Senior", "CV Sentosa", "Malang", "2026-09-01"),
        ),
        _capture(
            "https://lokerb.id/11",
            "lokerb.id",
            _posting("Staf Akuntansi Senior", "CV Sentosa", "Malang", "2026-09-02"),
        ),
        # Invalid: no employer.
        _capture(
            "https://lokerb.id/12", "lokerb.id", _posting("Kasir", "", "Malang", "2026-09-01")
        ),
    ]
    # A city-templated campaign: one site, one employer and role, many cities.
    for i, city in enumerate(["Wonosobo", "Pasuruan", "Kudus", "Blitar", "Kediri", "Madiun"]):
        rows.append(
            _capture(
                f"https://lokerc.id/kai-{i}",
                "lokerc.id",
                _posting(
                    f"Peluang Kerja Operasional PT KAI {city} 2025",
                    "PT Kereta Api Indonesia",
                    city,
                    "2026-09-01",
                ),
            )
        )
    # A site whose salaries are a theme default (identical range everywhere).
    for i in range(12):
        rows.append(
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
        )
    _write_bronze(lake, rows)
    return lake


def _query(lake: Lake, sql: str) -> list[tuple]:
    return duckdb.sql(sql.replace("{silver}", lake.silver.as_posix())).fetchall()


def test_deduplication_levels(lake: Lake) -> None:
    stats = build_silver(lake)
    assert stats.observations == 26 and stats.valid_observations == 25
    assert stats.source_records == 26
    # 3 Bandung records -> 1 opening; March Bandung -> 1; Surabaya -> 1; fuzzy pair -> 1;
    # KAI campaign -> 1; 12 distinct lokerd.id postings -> 12.
    assert stats.vacancies == 17
    multi_site = _query(
        lake,
        "select source_sites, source_records from '{silver}/vacancies.parquet' where source_records = 3",
    )
    assert multi_site == [(2, 3)]
    assert _query(lake, "select count(*) from '{silver}/vacancies.parquet' where merged_fuzzy") == [
        (1,)
    ]
    templated = _query(
        lake,
        "select city_templated, source_records from '{silver}/vacancies.parquet' where organization like '%Kereta%'",
    )
    assert templated == [(True, 6)]


def test_salary_template_sites_are_excluded_from_statistics(lake: Lake) -> None:
    build_silver(lake)
    reliable = dict(
        _query(
            lake,
            "select source_domain, bool_or(salary_reliable) from '{silver}/source_records.parquet' group by 1",
        )
    )
    assert reliable["lokerd.id"] is False
    assert reliable["lokera.id"] is True
    report = build_gold(lake)
    salary = duckdb.sql(
        f"select n, on_salary_template_sites from '{(lake.gold / 'salary_overall.parquet').as_posix()}'"
    ).fetchone()
    assert salary == (
        5,
        12,
    )  # 5 reliable vacancies; the 12 template-site ones are counted but excluded
    assert report["inventory"]["canonical_vacancies"] == 17
    assert report["invalid_reasons"] == {"missing_hiring_organization": 1}


def test_rebuild_is_idempotent_and_incremental(lake: Lake) -> None:
    first = build_silver(lake)
    assert parse_bronze(lake) == 0  # nothing new to parse
    second = build_silver(lake)
    assert (second.observations, second.vacancies) == (first.observations, first.vacancies)
    _write_bronze(
        lake,
        [
            _capture(
                "https://lokere.id/1",
                "lokere.id",
                _posting("Perawat", "RS Sehat", "Bogor", "2026-09-01"),
            )
        ],
        name="batch-2",
    )
    third = build_silver(lake)
    assert third.bronze_files_parsed == 1 and third.vacancies == first.vacancies + 1


def test_unchanged_recapture_counts_as_observation_not_vacancy(lake: Lake) -> None:
    first = build_silver(lake)
    target = lake.bronze / "commoncrawl" / "reobservations" / f"crawl={LATER_CRAWL}"
    target.mkdir(parents=True)
    rows = [
        {
            "crawl": LATER_CRAWL,
            "url": "https://lokera.id/1",
            "domain": "lokera.id",
            "index_fetch_time": datetime(2026, 10, 10, tzinfo=timezone.utc),
            "content_digest": f"sha1:{abs(hash('https://lokera.id/1'))}",
        }
    ]
    pq.write_table(pa.Table.from_pylist(rows), target / "r.parquet")
    second = build_silver(lake)
    assert second.observations == first.observations + 1
    assert second.vacancies == first.vacancies
    crawls = _query(
        lake, "select crawls from '{silver}/vacancies.parquet' where source_records = 3"
    )[0][0]
    assert sorted(crawls) == [CRAWL, LATER_CRAWL]


# --- collector -----------------------------------------------------------------------------


def _warc(url: str, html: str) -> bytes:
    record = (
        f"WARC/1.0\r\nWARC-Type: response\r\nWARC-Date: 2026-09-05T10:00:00Z\r\nWARC-Target-URI: {url}\r\n\r\n"
        f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n{html}"
    ).encode()
    return gzip.compress(record)


def _candidates(lake: Lake, urls: list[tuple[str, str]]) -> None:
    path = lake.cc_candidates(CRAWL)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "crawl": CRAWL,
            "url": url,
            "domain": domain,
            "fetch_time": datetime(2026, 9, 5, tzinfo=timezone.utc),
            "content_digest": f"d{i}",
            "warc_filename": f"w/{i}.warc.gz",
            "warc_record_offset": i,
            "warc_record_length": 10,
        }
        for i, (url, domain) in enumerate(urls)
    ]
    pq.write_table(pa.Table.from_pylist(rows), path)


def _fetcher(handler) -> ArchiveFetcher:  # type: ignore[no-untyped-def]
    return ArchiveFetcher(
        contact_url="https://example.org",
        workers=1,
        requests_per_second=1000,
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )


JOB_HTML = '<script type="application/ld+json">{"@type":"JobPosting","title":"Kasir","hiringOrganization":{"name":"Toko"}}</script>'


def test_collector_is_resumable_and_skips_no_yield_domains(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Yield is learned between batches; small batches let the skip rule act within this test.
    monkeypatch.setattr("talentscope.lake.commoncrawl.collect.BATCH_SIZE", 5)
    lake = Lake(tmp_path / "lake")
    lake.ensure()
    urls = [(f"https://jobs.id/{i}", "jobs-site.id") for i in range(3)]
    urls += [(f"https://news.id/{i}", "news.id") for i in range(MIN_DOMAIN_TRIALS + 5)]
    _candidates(lake, urls)

    def handler(request: httpx.Request) -> httpx.Response:
        index = int(request.url.path.rsplit("/", 1)[-1].split(".")[0])
        url, domain = urls[index]
        return httpx.Response(
            206, content=_warc(url, JOB_HTML if domain == "jobs-site.id" else "<p>berita</p>")
        )

    first = collect_crawl(lake, CRAWL, _fetcher(handler))
    assert first.pages_with_postings == 3
    # news.id produced nothing once MIN_DOMAIN_TRIALS of its pages were tried (checked
    # between batches), so its remaining pages were skipped.
    assert first.skipped_low_yield_domain > 0
    assert first.fetched + first.skipped_low_yield_domain == len(urls)
    second = collect_crawl(lake, CRAWL, _fetcher(handler))
    assert second.fetched == 0 and second.already_fetched == first.fetched


def test_collector_stops_on_403_and_retries_later(tmp_path: Path) -> None:
    lake = Lake(tmp_path / "lake")
    lake.ensure()
    urls = [(f"https://jobs.id/{i}", "jobs-site.id") for i in range(6)]
    _candidates(lake, urls)
    calls = {"n": 0}

    def blocking(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return (
            httpx.Response(206, content=_warc("u", JOB_HTML))
            if calls["n"] <= 2
            else httpx.Response(403)
        )

    stats = collect_crawl(lake, CRAWL, _fetcher(blocking))
    assert stats.blocked and stats.fetched == 2
    assert calls["n"] == 3  # no requests after the block

    def healthy(request: httpx.Request) -> httpx.Response:
        return httpx.Response(206, content=_warc("u", JOB_HTML))

    resumed = collect_crawl(lake, CRAWL, _fetcher(healthy))
    assert resumed.already_fetched == 2 and resumed.fetched == 4 and not resumed.blocked


def test_transient_failures_are_retried_on_the_next_run(tmp_path: Path) -> None:
    lake = Lake(tmp_path / "lake")
    lake.ensure()
    _candidates(lake, [("https://jobs.id/0", "jobs-site.id")])
    failing = _fetcher(lambda request: httpx.Response(503))
    first = collect_crawl(lake, CRAWL, failing)
    assert first.failures == {"http_503": 1}
    second = collect_crawl(
        lake, CRAWL, _fetcher(lambda request: httpx.Response(206, content=_warc("u", JOB_HTML)))
    )
    assert second.fetched == 1 and second.pages_with_postings == 1


def test_sites_excluded_later_disappear_from_silver(
    lake: Lake, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = build_silver(lake)
    monkeypatch.setattr("talentscope.lake.silver.EXCLUDED_DOMAINS", frozenset({"lokerd.id"}))
    after = build_silver(lake)
    assert after.vacancies == before.vacancies - 12
    assert _query(
        lake,
        "select count(*) from '{silver}/source_records.parquet' where source_domain = 'lokerd.id'",
    ) == [(0,)]


def test_jsonl_import_flows_into_silver(tmp_path: Path) -> None:
    from talentscope.lake.imports import import_jsonl

    lake = Lake(tmp_path / "lake")
    lake.ensure()
    export = tmp_path / "export.jsonl"
    good = _posting("Data Analyst", "PT Licensed", "Jakarta Selatan", "2026-09-01")
    lines = [
        json.dumps(
            {
                **good,
                "url": "https://provider.example/jobs/1",
                "captured_at": "2026-09-02T00:00:00Z",
            }
        ),
        json.dumps({**good, "url": "not-a-url", "captured_at": "2026-09-02T00:00:00Z"}),
        json.dumps({**good, "url": "https://provider.example/jobs/2"}),
        "[1, 2]",
        "",
    ]
    export.write_text("\n".join(lines), encoding="utf-8")
    stats = import_jsonl(lake, "licensed-feed", export)
    assert (stats.lines, stats.imported, stats.rejected) == (4, 1, 3)
    assert import_jsonl(lake, "licensed-feed", export).already_imported
    silver = build_silver(lake)
    assert silver.vacancies == 1
    assert _query(
        lake, "select registry_source_id, source_domain from '{silver}/vacancies.parquet'"
    ) == [("licensed-feed", "provider.example")]


def test_representative_is_deterministic_when_dates_tie(tmp_path: Path) -> None:
    lake = Lake(tmp_path / "lake")
    lake.ensure()
    # Same vacancy on two sites, same posting date and capture time: only the record key
    # can break the tie, so every rebuild must pick the same representative.
    _write_bronze(
        lake,
        [
            _capture(
                "https://lokerz.id/7",
                "lokerz.id",
                _posting("Kasir", "PT Toko", "Depok", "2026-09-01", (3_000_000, 3_500_000)),
            ),
            _capture(
                "https://lokera.id/7",
                "lokera.id",
                _posting("Kasir", "PT Toko", "Depok", "2026-09-01", (3_200_000, 3_600_000)),
            ),
        ],
    )
    sql = "select source_domain, salary_min, sites, member_keys from '{silver}/vacancies.parquet'"
    build_silver(lake, full=True)
    first = _query(lake, sql)
    build_silver(lake, full=True)
    assert _query(lake, sql) == first
    assert first[0][:3] == ("lokera.id", 3_200_000, ["lokera.id", "lokerz.id"])


@pytest.mark.parametrize("status", [None, ReviewStatus.PROHIBITS, ReviewStatus.UNREADABLE])
def test_archived_pages_need_a_usable_site_review(
    lake: Lake, monkeypatch: pytest.MonkeyPatch, status: ReviewStatus | None
) -> None:
    before = build_silver(lake)
    if status is None:
        monkeypatch.delitem(DOMAIN_REVIEWS, "lokerd.id")  # never reviewed: default deny
    else:
        monkeypatch.setitem(DOMAIN_REVIEWS, "lokerd.id", DomainReview(status))
    after = build_silver(lake)
    assert after.vacancies == before.vacancies - 12
    assert _query(
        lake, "select count(*) from '{silver}/vacancies.parquet' where source_domain = 'lokerd.id'"
    ) == [(0,)]


def _campaign_lake(tmp_path: Path, salaries: list[tuple[int, int] | None]) -> Lake:
    lake = Lake(tmp_path / "lake")
    lake.ensure()
    cities = ["Bandung", "Bogor", "Depok", "Bekasi", "Cirebon", "Garut", "Tasikmalaya"]
    rows = [
        _capture(
            f"https://lokera.id/driver-{city.lower()}",
            "lokera.id",
            _posting(f"Driver {city}", "PT Cepat Logistik", city, "2026-09-01", salary),
        )
        for city, salary in zip(cities, salaries, strict=False)
    ]
    _write_bronze(lake, rows)
    build_silver(lake)
    return lake


def test_copied_pages_for_many_places_are_one_campaign(tmp_path: Path) -> None:
    lake = _campaign_lake(tmp_path, [(3_000_000, 3_500_000)] * 6)
    assert _query(
        lake, "select count(*), bool_and(city_templated) from '{silver}/vacancies.parquet'"
    ) == [(1, True)]


def test_regional_salaries_mean_separate_local_openings(tmp_path: Path) -> None:
    # Same employer and role in six cities, but each city pays differently: these are
    # genuine location-specific openings, not an SEO copy campaign.
    salaries = [(3_000_000 + i * 250_000, 3_500_000 + i * 250_000) for i in range(6)]
    lake = _campaign_lake(tmp_path, salaries)
    assert _query(
        lake, "select count(*), bool_or(city_templated) from '{silver}/vacancies.parquet'"
    ) == [(6, False)]


def test_few_places_stay_separate_even_when_copied(tmp_path: Path) -> None:
    lake = _campaign_lake(tmp_path, [(3_000_000, 3_500_000)] * 4)
    assert _query(lake, "select count(*) from '{silver}/vacancies.parquet'") == [(4,)]


def _deadline_capture(
    site: str, i: int, posted: str, valid_through: str, *, title: str | None = None
) -> dict:
    posting = _posting(title or f"Posisi {i}", f"PT Usaha {site} {i}", "Medan", posted)
    posting["validThrough"] = valid_through
    return _capture(f"https://{site}/{i}", site, posting)


def _deadline_flags(lake: Lake) -> dict[str, tuple[bool, bool]]:
    rows = _query(
        lake,
        "select source_domain, bool_or(deadline_template_site), bool_or(valid_through_reliable) "
        "from '{silver}/source_records.parquet' group by 1",
    )
    return {site: (template, reliable) for site, template, reliable in rows}


def test_theme_default_deadlines_are_marked_unreliable(tmp_path: Path) -> None:
    lake = Lake(tmp_path / "lake")
    lake.ensure()
    days = [f"2026-08-{day:02d}" for day in range(1, 29)]
    rows = (
        # One fixed validThrough on every page (bisakerja.id-style theme default).
        [_deadline_capture("lokera.id", i, day, "2026-12-31") for i, day in enumerate(days)]
        # validThrough = datePosted + 60 days on a third of the pages, the rest varied
        # (lokerbekasi.my.id-style): a default offset.
        + [
            _deadline_capture(
                "lokerb.id",
                i,
                day,
                (date.fromisoformat(day) + timedelta(days=60 if i % 3 == 0 else 5 + i)).isoformat(),
            )
            for i, day in enumerate(days)
        ]
        # Employer deadlines: different dates and offsets.
        + [
            _deadline_capture(
                "lokerc.id",
                i,
                day,
                (date.fromisoformat(day) + timedelta(days=7 + 2 * i)).isoformat(),
            )
            for i, day in enumerate(days)
        ]
    )
    _write_bronze(lake, rows)
    build_silver(lake)
    assert _deadline_flags(lake) == {
        "lokera.id": (True, False),
        "lokerb.id": (True, False),
        "lokerc.id": (False, True),
    }
    # The source value is kept; only its use as a deadline changes.
    assert _query(
        lake,
        "select count(*) from '{silver}/vacancies.parquet' "
        "where source_domain = 'lokera.id' and valid_through = date '2026-12-31'",
    ) == [(28,)]
    report = build_gold(lake)
    assert report["inventory"]["deadline_template_sites"] == ["lokera.id", "lokerb.id"]
    assert report["inventory"]["vacancies_with_template_deadline"] == 56
    assert report["completeness_of_vacancies"]["valid_through_reliable"] == round(28 / 84, 4)


def test_few_shared_deadlines_do_not_make_a_template_site(tmp_path: Path) -> None:
    # Below DEADLINE_TEMPLATE_MIN_RECORDS a shared date is plausibly one employer's batch.
    lake = Lake(tmp_path / "lake")
    lake.ensure()
    _write_bronze(
        lake, [_deadline_capture("lokera.id", i, "2026-08-01", "2026-09-30") for i in range(19)]
    )
    build_silver(lake)
    assert _deadline_flags(lake) == {"lokera.id": (False, True)}


def test_implausibly_low_salaries_are_unreliable_with_a_reason(tmp_path: Path) -> None:
    lake = Lake(tmp_path / "lake")
    lake.ensure()
    _write_bronze(
        lake,
        [
            _capture(
                "https://lokera.id/1",
                "lokera.id",
                _posting("Customer Relations", "PT Satu", "Bekasi", "2026-09-01", (2, 897)),
            ),
            _capture(
                "https://lokera.id/2",
                "lokera.id",
                _posting("Kasir", "PT Dua", "Bekasi", "2026-09-01", (4_000_000, 4_500_000)),
            ),
        ],
    )
    build_silver(lake)
    rows = _query(
        lake,
        "select title, salary_reliable, salary_unreliable_reason "
        "from '{silver}/vacancies.parquet' order by title",
    )
    assert rows == [
        ("Customer Relations", False, "BELOW_MONTHLY_FLOOR"),
        ("Kasir", True, None),
    ]


def test_campaign_is_one_vacancy_across_page_generation_batches(tmp_path: Path) -> None:
    # The same SEO campaign generated in two batches months apart, with rotating title
    # words ("Terkini", "Terupdate"): still one campaign, not one vacancy per batch/word.
    lake = Lake(tmp_path / "lake")
    lake.ensure()
    places = ["Bandung", "Bogor", "Depok", "Bekasi", "Cirebon", "Garut"]
    rows = [
        _capture(
            f"https://lokera.id/art-{batch}-{place.lower()}",
            "lokera.id",
            _posting(
                f"{word} ART (Pembantu Rumah Tangga) {place}",
                "Perorangan",
                place,
                posted,
                None,
            ),
        )
        for batch, (word, posted) in enumerate(
            [("Terkini", "2023-10-17"), ("Terupdate", "2024-07-03")]
        )
        for place in places
    ]
    _write_bronze(lake, rows)
    build_silver(lake)
    assert _query(
        lake,
        "select count(*), bool_and(city_templated), sum(source_records) "
        "from '{silver}/vacancies.parquet'",
    ) == [(1, True, 12)]


def test_non_campaign_reposts_are_still_split_by_the_window(tmp_path: Path) -> None:
    lake = Lake(tmp_path / "lake")
    lake.ensure()
    _write_bronze(
        lake,
        [
            _capture(
                f"https://lokera.id/{i}",
                "lokera.id",
                _posting("Admin Gudang", "PT Maju", "Bandung", posted),
            )
            for i, posted in enumerate(["2026-01-05", "2026-01-20", "2026-06-01"])
        ],
    )
    assert build_silver(lake).vacancies == 2


def test_employer_display_name_is_the_same_on_every_rebuild(tmp_path: Path) -> None:
    lake = Lake(tmp_path / "lake")
    lake.ensure()
    _write_bronze(
        lake,
        [
            _capture(
                f"https://lokera.id/{i}",
                "lokera.id",
                _posting(title, org, "Bandung", "2026-09-01"),
            )
            for i, (title, org) in enumerate(
                [
                    ("Kasir", "PT. Maju Jaya"),
                    ("Admin Gudang", "PT Maju Jaya"),
                    ("Sopir", "PT MAJU JAYA"),
                ]
            )
        ],
    )
    build_silver(lake)
    employers = (lake.gold / "employers.parquet").as_posix()
    names = set()
    for _ in range(3):
        build_gold(lake)
        names.add(duckdb.sql(f"select organization, vacancies from '{employers}'").fetchall()[0])
    assert names == {("PT MAJU JAYA", 3)}
