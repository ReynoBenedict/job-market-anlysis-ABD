import gzip
import json
from datetime import datetime, timezone

import pytest

from talentscope.lake.commoncrawl.warc import FetchFailed, parse_warc_record
from talentscope.lake.domains import is_excluded, site_type
from talentscope.lake.jsonld import extract_job_postings
from talentscope.lake.postings import (
    canonical_page_url,
    normalize_posting,
    resolve_place,
    title_key,
)
from talentscope.lake.skills import extract_skills

CAPTURED = datetime(2026, 9, 10, tzinfo=timezone.utc)


def _posting(**overrides: object) -> dict:
    posting: dict = {
        "@type": "JobPosting",
        "title": "Lowongan Kerja Admin Gudang PT Contoh Sejahtera Bandung",
        "hiringOrganization": {"@type": "Organization", "name": "PT Contoh Sejahtera"},
        "jobLocation": {
            "@type": "Place",
            "address": {
                "addressLocality": "Bandung",
                "addressRegion": "Jawa Barat",
                "addressCountry": "ID",
            },
        },
        "datePosted": "2026-09-01",
        "validThrough": "2026-10-01",
        "employmentType": "FULL_TIME",
        "baseSalary": {
            "@type": "MonetaryAmount",
            "currency": "IDR",
            "value": {
                "@type": "QuantitativeValue",
                "minValue": 4000000,
                "maxValue": 5000000,
                "unitText": "MONTH",
            },
        },
        "description": "<p>Menguasai Microsoft Excel dan SAP. Memiliki SIM C.</p>" + "x" * 100,
    }
    posting.update(overrides)
    return posting


def _normalize(posting: dict) -> dict:
    row = normalize_posting(
        posting,
        page_url="https://lokercontoh.id/admin-gudang/",
        domain="lokercontoh.id",
        captured_at=CAPTURED,
        position=0,
    )
    return {**row.values, "invalid": row.invalid_reasons, "flags": row.quality_flags}


def test_jsonld_extraction_handles_graph_lists_and_bad_blocks() -> None:
    html = b"""
    <script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"WebPage"},
      {"@type":"JobPosting","title":"A"}]}</script>
    <script type='application/ld+json'>[{"@type":["JobPosting"],"title":"B\twith tab"}]</script>
    <script type="application/ld+json">{"@type": "JobPosting", broken}</script>
    <script type="application/ld+json">{"@type":"Organization"}</script>
    """
    postings, malformed = extract_job_postings(html)
    assert [p["title"] for p in postings] == ["A", "B\twith tab"]
    assert malformed == 1


def test_warc_record_parsing() -> None:
    record = (
        b"WARC/1.0\r\nWARC-Type: response\r\nWARC-Date: 2026-09-05T10:00:00Z\r\n"
        b"WARC-Target-URI: https://lokercontoh.id/a\r\n\r\n"
        b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html>body</html>"
    )
    capture = parse_warc_record(record)
    assert capture.target_uri == "https://lokercontoh.id/a"
    assert capture.captured_at == datetime(2026, 9, 5, 10, tzinfo=timezone.utc)
    assert (capture.http_status, capture.body) == (200, b"<html>body</html>")
    assert gzip.compress(
        record
    )  # the fetcher stores gzip members; parsing takes the decompressed bytes


def test_non_response_warc_record_is_rejected() -> None:
    with pytest.raises(FetchFailed, match="not_a_response_record"):
        parse_warc_record(b"WARC/1.0\r\nWARC-Type: request\r\n\r\nGET / HTTP/1.1\r\n\r\n")


def test_full_posting_normalization() -> None:
    row = _normalize(_posting())
    assert row["invalid"] == []
    assert (row["organization"], row["city"], row["province"]) == (
        "PT Contoh Sejahtera",
        "Bandung",
        "Jawa Barat",
    )
    assert (row["salary_monthly_min"], row["salary_monthly_max"], row["salary_currency"]) == (
        4_000_000,
        5_000_000,
        "IDR",
    )
    assert row["employment_type"] == "FULL_TIME"
    assert row["role_family"] == "SUPPLY_CHAIN"
    assert row["title_key"] == "admin gudang"
    assert {"Microsoft Excel", "SAP", "Driving License (SIM)"} <= set(row["skills"])
    assert row["source_record_key"] == "https://lokercontoh.id/admin-gudang#0"
    assert row["flags"] == []


def test_identifier_value_is_read_but_identity_stays_url_based() -> None:
    # PropertyValue.name is usually the employer; only `value` is the identifier. Identity
    # stays URL-based because repost blogs emit template identifiers such as "1".
    row = _normalize(
        _posting(identifier={"@type": "PropertyValue", "name": "Contoh", "value": "JOB-42"})
    )
    assert row["source_identifier"] == "JOB-42"
    assert (row["source_record_key"], row["record_key_kind"]) == (
        "https://lokercontoh.id/admin-gudang#0",
        "page_url",
    )


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"title": ""}, "missing_title"),
        ({"hiringOrganization": None}, "missing_hiring_organization"),
        ({"title": "Tips Cara Membuat CV yang Menarik"}, "not_a_vacancy"),
        (
            {
                "jobLocation": {
                    "address": {"addressLocality": "Kuala Lumpur", "addressCountry": "MY"}
                }
            },
            "location_outside_indonesia",
        ),
    ],
)
def test_invalid_postings_are_rejected_with_reason(overrides: dict, reason: str) -> None:
    assert reason in _normalize(_posting(**overrides))["invalid"]


def test_missing_salary_is_not_zero() -> None:
    row = _normalize(_posting(baseSalary=None))
    assert row["salary_status"] == "NOT_DISCLOSED"
    assert row["salary_monthly_min"] is None and row["salary_min"] is None


def test_salary_units_currency_aliases_and_zero() -> None:
    yearly = _normalize(
        _posting(baseSalary={"currency": "Rp", "value": {"value": 120_000_000, "unitText": "YEAR"}})
    )
    assert (yearly["salary_currency"], yearly["salary_monthly_min"]) == ("IDR", 10_000_000)
    hourly = _normalize(
        _posting(baseSalary={"currency": "IDR", "value": {"value": 50_000, "unitText": "HOUR"}})
    )
    assert hourly["salary_monthly_min"] is None and hourly["salary_period"] == "HOUR"
    usd = _normalize(
        _posting(
            baseSalary={
                "currency": "USD",
                "value": {"minValue": 1000, "maxValue": 2000, "unitText": "MONTH"},
            }
        )
    )
    assert (
        usd["salary_min"] == 1000 and usd["salary_monthly_min"] is None
    )  # not comparable with IDR stats
    zero = _normalize(
        _posting(baseSalary={"currency": "IDR", "value": {"value": 0, "unitText": "MONTH"}})
    )
    assert zero["salary_status"] == "INVALID"
    no_unit = _normalize(_posting(baseSalary={"currency": "IDR", "value": 5_000_000}))
    assert "SALARY_PERIOD_MISSING" in no_unit["flags"] and no_unit["salary_monthly_min"] is None


def test_dates_are_validated() -> None:
    future = _normalize(_posting(datePosted="2030-01-01"))
    assert future["date_posted"] is None and "DATE_POSTED_IMPLAUSIBLE" in future["flags"]
    garbage = _normalize(_posting(datePosted="kemarin"))
    assert "DATE_POSTED_UNPARSEABLE" in garbage["flags"]
    expired = _normalize(_posting(validThrough="2026-09-05"))
    assert "EXPIRED_AT_CAPTURE" in expired["flags"]
    reversed_dates = _normalize(_posting(validThrough="2026-08-01"))
    assert (
        reversed_dates["valid_through"] is None
        and "VALID_THROUGH_BEFORE_POSTED" in reversed_dates["flags"]
    )


def test_multi_location_and_remote() -> None:
    row = _normalize(
        _posting(
            jobLocation=[
                {"address": {"addressLocality": "Bandung", "addressRegion": "Jawa Barat"}},
                {"address": {"addressLocality": "Surabaya", "addressRegion": "Jawa Timur"}},
            ],
            jobLocationType="TELECOMMUTE",
        )
    )
    assert row["provinces"] == ["Jawa Barat", "Jawa Timur"] and "MULTI_LOCATION" in row["flags"]
    assert row["work_arrangement"] == "REMOTE"


@pytest.mark.parametrize(
    ("locality", "region", "expected"),
    [
        ("Jakarta, Daerah Khusus Ibukota Jakarta, Indonesia", None, (None, "DKI Jakarta")),
        ("Kabupaten Sukoharjo", "Jawa Tengah", ("Kabupaten Sukoharjo", "Jawa Tengah")),
        ("Seluruh Indonesia", None, (None, None)),
        ("Kota Bekasi", None, ("Kota Bekasi", "Jawa Barat")),
        (None, None, (None, None)),
    ],
)
def test_place_resolution(locality: str | None, region: str | None, expected: tuple) -> None:
    assert resolve_place(locality, region) == expected


def test_title_key_matches_city_templated_and_reposted_titles() -> None:
    org = "PT KERETA API INDONESIA (PERSERO)"
    a = title_key(
        "Karir Tanpa Syarat Rumit Operasional Kereta Api PT KAI Pasuruan tahun 2025",
        org,
        ("Pasuruan",),
    )
    b = title_key(
        "Peluang Kerja Operasional Kereta Api PT KAI Wonosobo tahun 2025", org, ("Wonosobo",)
    )
    assert a == b == "operasional kai"


def test_skill_patterns_avoid_ambiguous_matches() -> None:
    assert extract_skills("Pengalaman JavaScript dan React Native, bukan Java") == [
        "Java",
        "JavaScript",
        "React Native",
    ]
    assert extract_skills("Javascript developer") == ["JavaScript"]
    assert extract_skills("Mampu go ke lapangan, R&D, mengetik di Word") == []
    assert extract_skills("C++ dan C# serta .NET") == ["C#", "C++", ".NET"]
    assert extract_skills(None) == []
    # False positives found in the reviewed sample (docs/ml/SKILL_EXTRACTION_REVIEW.md):
    assert extract_skills("mengelola jaringan komunikasi kantor") == []
    assert extract_skills("spreadsheet akan jadi teman terbaikmu") == []
    assert extract_skills("Minimal S1 di bidang Bahasa Inggris, Komunikasi") == []
    assert extract_skills("Pendidikan D3 Akuntansi. Menguasai Excel") == ["Microsoft Excel"]
    assert extract_skills("Pendidikan S1. Mampu berbahasa Inggris (English) aktif") == ["English"]


def test_canonical_url() -> None:
    assert (
        canonical_page_url("HTTPS://LokerContoh.id/Admin-Gudang/?a=1#top")
        == "https://lokercontoh.id/Admin-Gudang?a=1"
    )


def test_domain_policy() -> None:
    assert is_excluded("jobstreet.co.id") and is_excluded("Kalibrr.id") and is_excluded(None)
    assert not is_excluded("lokercontoh.id")
    assert site_type("lokerbandung.id") == "job_site" and site_type("rsuhermina.co.id") == "other"


def test_postings_round_trip_through_json() -> None:
    posting = _posting()
    assert json.loads(json.dumps([posting]))[0]["title"] == posting["title"]


def test_resolve_place_handles_english_spellings_and_jakarta_districts() -> None:
    assert resolve_place("Medan, Sumatra Utara", None) == ("Medan", "Sumatera Utara")
    assert resolve_place("Kalideres", None) == ("Kalideres", "DKI Jakarta")
    assert resolve_place("Cikarang Barat", "West Java") == ("Cikarang Barat", "Jawa Barat")


@pytest.mark.parametrize(
    "organization",
    ["Perusahaan", "Company", "Lokercontoh", "Lokercontoh Jobs"],
)
def test_placeholder_employers_are_invalid(organization: str) -> None:
    # The page's own site (lokercontoh.id) or a generic word is not an employer.
    row = _normalize(_posting(hiringOrganization={"@type": "Organization", "name": organization}))
    assert row["invalid"] == ["placeholder_hiring_organization"]


def test_real_employer_sharing_a_word_with_the_site_is_kept() -> None:
    row = _normalize(_posting(hiringOrganization={"name": "PT Lokercontoh Abadi"}))
    assert row["invalid"] == []


def test_html_entities_in_titles_are_decoded() -> None:
    row = _normalize(_posting(title="Barista &#8211; Fulltime &amp; Part Time"))
    assert row["title"] == "Barista – Fulltime & Part Time"


def test_title_key_drops_the_district_of_seo_pages() -> None:
    # SEO pages repeat one title per district; only the district differs between them.
    keys = {
        title_key(
            f"Info Loker Indomaret {district}, Purworejo, Jawa Tengah",
            "Indomaret",
            (district, "Purworejo", "Jawa Tengah"),
        )
        for district in ("Pituruh", "Kutoarjo", "Bayan")
    }
    assert len(keys) == 1


def test_agency_recruiting_on_its_own_site_is_an_employer() -> None:
    row = normalize_posting(
        _posting(hiringOrganization={"name": "JAC Recruitment Indonesia"}),
        page_url="https://jac-recruitment.co.id/jobs/1",
        domain="jac-recruitment.co.id",
        captured_at=CAPTURED,
        position=0,
    )
    assert row.invalid_reasons == []


@pytest.mark.parametrize(
    ("organization", "shown_as", "flag"),
    [
        ("ART (Pembantu Rumah Tangga)", "Perorangan (rumah tangga)", "EMPLOYER_HOUSEHOLD"),
        ("Dirahasiakan", "Perusahaan dirahasiakan", "EMPLOYER_CONFIDENTIAL"),
        ("Confidential", "Perusahaan dirahasiakan", "EMPLOYER_CONFIDENTIAL"),
    ],
)
def test_household_and_confidential_employers_are_real_vacancies(
    organization: str, shown_as: str, flag: str
) -> None:
    # An occupation in the employer field (a household hiring a domestic worker) or a
    # withheld company name is still a genuine vacancy, unlike a filler such as "Perusahaan".
    row = _normalize(
        _posting(
            title="ART (Pembantu Rumah Tangga) Pandak", hiringOrganization={"name": organization}
        )
    )
    assert row["invalid"] == []
    assert row["organization"] == shown_as
    assert flag in row["flags"]


def test_double_encoded_text_is_repaired() -> None:
    row = _normalize(_posting(title="Pramusaji Warung Makan (YANTI â€“ BOGOR)"))
    assert row["title"] == "Pramusaji Warung Makan (YANTI – BOGOR)"
    plain = _normalize(_posting(title="Kasir Toko Kue – Bogor"))  # already correct: unchanged
    assert plain["title"] == "Kasir Toko Kue – Bogor"
