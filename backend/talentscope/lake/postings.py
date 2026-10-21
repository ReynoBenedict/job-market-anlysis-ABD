"""Parse and validate one schema.org JobPosting object into a flat silver row.

Values are taken only from the markup; nothing is inferred beyond documented rules
(province from a known city, Indonesia from a resolved province). Missing values stay
None. Each row carries `invalid_reasons` (row excluded from vacancy counts) and
`quality_flags` (row kept, but the issue is reported).
"""

from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from talentscope.lake.skills import extract_skills
from talentscope.normalization.attributes import normalize_education
from talentscope.normalization.location import canonical_city, canonical_province, parse_location
from talentscope.normalization.role_family import classify_role_family
from talentscope.normalization.salary import evaluate_salary_amounts
from talentscope.normalization.text import clean_text, normalize_for_matching
from talentscope.vocab import (
    EducationLevel,
    EmploymentType,
    SalaryPeriod,
    SalaryStatus,
    WorkArrangement,
)

PARSER_VERSION = "jobposting-silver/15"

_EMPLOYMENT_TYPES = {
    "FULL_TIME": EmploymentType.FULL_TIME,
    "FULLTIME": EmploymentType.FULL_TIME,
    "PART_TIME": EmploymentType.PART_TIME,
    "PARTTIME": EmploymentType.PART_TIME,
    "CONTRACTOR": EmploymentType.CONTRACT,
    "CONTRACT": EmploymentType.CONTRACT,
    "TEMPORARY": EmploymentType.TEMPORARY,
    "INTERN": EmploymentType.INTERNSHIP,
    "INTERNSHIP": EmploymentType.INTERNSHIP,
    "VOLUNTEER": EmploymentType.VOLUNTEER,
    "PER_DIEM": EmploymentType.TEMPORARY,
}
_SALARY_UNITS = {
    "HOUR": SalaryPeriod.HOUR,
    "DAY": SalaryPeriod.DAY,
    "WEEK": SalaryPeriod.WEEK,
    "MONTH": SalaryPeriod.MONTH,
    "YEAR": SalaryPeriod.YEAR,
}
_INDONESIA = {"id", "idn", "indonesia", "republic of indonesia", "republik indonesia"}
# Location values meaning "anywhere in Indonesia": Indonesian, but no single place.
_NATIONWIDE = {
    "seluruh indonesia",
    "semua kota",
    "seluruh wilayah indonesia",
    "nasional",
    "nationwide",
}
_CURRENCY_ALIASES = {"RP": "IDR", "RP.": "IDR", "RUPIAH": "IDR", "US$": "USD", "$": "USD"}
# Titles of articles that job blogs mark up as JobPosting but that are not vacancies.
_NOT_A_VACANCY = re.compile(
    r"\b(tips|cara (?:membuat|menulis|daftar|melamar)|contoh surat|kisi[- ]kisi|kunci jawaban|"
    r"soal (?:tes|psikotes)|hasil seleksi|pengumuman (?:hasil|kelulusan)|daftar gaji|jadwal tes)\b",
    re.IGNORECASE,
)
# Words that job blogs wrap around the actual role ("Lowongan Kerja Admin PT X Bandung"),
# including the rotating SEO phrases of city-templated pages ("Karir Tanpa Syarat Rumit",
# "Terkini ART ...", "Terupdate ART ...").
_TITLE_NOISE = re.compile(
    r"\b(lowongan|loker|kerja|kerjaan|karir|karier|peluang|info|terbaru|dibutuhkan|dicari|"
    r"urgent|segera|hiring|vacancy|job|di|untuk|bulan|tahun|20\d\d|tanpa|syarat|rumit|"
    r"terkini|terupdate|lulusan|semua|jurusan|pendaftaran|rekrutmen|penerimaan|dibuka|buka|kota|kabupaten|kab)\b"
)
# Employer names that are placeholders rather than an employer (seen in real pages): a
# generic word, "confidential", or a job category. The site's own name is also treated
# as a placeholder (see _is_placeholder_organization).
_PLACEHOLDER_ORGANIZATIONS = frozenset({"perusahaan", "perusahaan swasta", "company"})
# Not placeholders: real vacancies whose employer is withheld or is a private household.
# They stay valid, with the employer shown under a neutral name and a quality flag.
_CONFIDENTIAL_EMPLOYER = frozenset(
    {"rahasia", "dirahasiakan", "confidential", "perusahaan dirahasiakan"}
)
_HOUSEHOLD_EMPLOYER = frozenset(
    {"art pembantu rumah tangga", "pembantu rumah tangga", "rumah tangga", "perorangan"}
)
CONFIDENTIAL_EMPLOYER_NAME = "Perusahaan dirahasiakan"
HOUSEHOLD_EMPLOYER_NAME = "Perorangan (rumah tangga)"
_TAG = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"\s+")
EARLIEST_PLAUSIBLE_POSTING = date(2010, 1, 1)
FUTURE_TOLERANCE = timedelta(days=2)


@dataclass
class PostingRow:
    values: dict[str, Any]
    invalid_reasons: list[str] = field(default_factory=list)
    quality_flags: list[str] = field(default_factory=list)


def _text(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("name") or value.get("value") or value.get("@value")
    if isinstance(value, list):
        value = next((v for v in value if isinstance(v, (str, dict))), None)
        return _text(value)
    # JSON-LD written by blog themes often carries HTML entities ("Barista &#8211; Fulltime").
    return (
        clean_text(_repair_mojibake(html.unescape(str(value))))
        if isinstance(value, (str, int, float))
        else None
    )


_MOJIBAKE = re.compile("[ÂÃ][\u0080-¿]|â€")


def _repair_mojibake(text: str) -> str:
    """Undo UTF-8 text that a site decoded as Windows-1252 ("YANTI â€“ BOGOR"). Only
    applied when the telltale sequences are present and the round trip is clean."""
    if not _MOJIBAKE.search(text):
        return text
    try:
        return text.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def _identifier(value: Any) -> str | None:
    """schema.org identifier: a string, or a PropertyValue whose `value` (not `name`,
    which is usually the employer) is the ID."""
    if isinstance(value, dict):
        return clean_text(
            value.get("value") if value.get("value") is not None else value.get("@value")
        )
    if isinstance(value, list):
        return next((i for i in map(_identifier, value) if i), None)
    return clean_text(value) if isinstance(value, (str, int)) else None


def description_text(value: Any) -> str | None:
    """Plain text from an HTML (often double-escaped) description."""
    raw = _text(value) if not isinstance(value, str) else value
    if not raw:
        return None
    text = html.unescape(html.unescape(raw))
    text = _TAG.sub(" ", text)
    return _SPACES.sub(" ", text).strip() or None


def _parse_date(value: Any) -> date | None:
    text = _text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return parsed.date()


def canonical_page_url(url: str) -> str:
    """Scheme/host lower-cased, fragment dropped, trailing slash removed."""
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def title_key(title: str, organization: str | None, places: tuple[str | None, ...] = ()) -> str:
    """Title stripped of blog boilerplate, the employer's name, and the posting's own place
    names, so the same role matches across sites and across city-templated pages."""
    key = normalize_for_matching(title)
    for name in (organization, *places):
        for token in normalize_for_matching(name).split():
            if len(token) > 2 and token not in {"pt", "cv", "tbk"}:
                key = re.sub(rf"\b{re.escape(token)}\b", " ", key)
    key = _TITLE_NOISE.sub(" ", key)
    key = re.sub(r"\b(pt|cv|tbk)\b", " ", key)
    return _SPACES.sub(" ", key).strip()


# Words a job board adds to its own name ("Lorong Jobs"). A company name with only
# "Indonesia" added (an agency recruiting on its own site) is a real employer.
_SITE_NAME_WORDS = re.compile(r"\b(?:jobs?|loker|lowongan|karir|karier|careers?|info)\b")


# Blog boilerplate around the actual job title, seen on archived regional job sites.
_TITLE_PREFIX = re.compile(
    r"^(?:info\s+)?(?:lowongan(?:\s+kerja)?|loker)\s+(?:terbaru\s+)?", re.IGNORECASE
)
_TITLE_SUFFIXES = (
    re.compile(r"\s+[-–|]\s+(?:bisa kerja|loker\w*|info loker.*)$", re.IGNORECASE),
    re.compile(r",\s*info loker.*$", re.IGNORECASE),
    re.compile(r"\s*\((?:lamar sekarang|resmi)\)$", re.IGNORECASE),
    re.compile(r"\s+(?:terbaru\s+)?(?:tahun\s+)?20\d\d$", re.IGNORECASE),
)


def display_title(title: str, organization: str | None) -> str:
    """The title without site boilerplate ("Lowongan Kerja ... (Lamar Sekarang) - Bisa
    Kerja") and without the employer name repeated twice. Wording and casing are
    otherwise unchanged; the original title is kept as ``source_title``."""
    cleaned = title.strip()
    for pattern in _TITLE_SUFFIXES:
        cleaned = pattern.sub("", cleaned).strip()
    cleaned = _TITLE_PREFIX.sub("", cleaned).strip()
    cleaned = re.sub(r"^20\d\d\s+(?:di\s+)?", "", cleaned)
    if organization and cleaned.lower().count(organization.lower()) > 1:
        cut = cleaned.lower().rfind(organization.lower())
        cleaned = (cleaned[:cut] + cleaned[cut + len(organization) :]).strip(" ,")
    cleaned = re.sub(r"\s+,", ",", re.sub(r"\s{2,}", " ", cleaned))
    if len(cleaned) < 3:
        return title.strip()
    return cleaned[0].upper() + cleaned[1:]


def _is_placeholder_organization(organization: str, domain: str) -> bool:
    """A generic word, or the site's own name (e.g. "Lorong Jobs" on lorong.my.id)."""
    name = normalize_for_matching(organization)
    if name in _PLACEHOLDER_ORGANIZATIONS:
        return True
    site = normalize_for_matching(domain.split(".")[0]).replace(" ", "")
    bare = _SITE_NAME_WORDS.sub(" ", name).replace(" ", "")
    return name.replace(" ", "") == site or (bool(bare) and bare == _SITE_NAME_WORDS.sub("", site))


def organization_key(organization: str | None) -> str:
    key = normalize_for_matching(organization)
    key = re.sub(r"\b(pt|cv|tbk|persero|perseroda|indonesia)\b", " ", key)
    return _SPACES.sub(" ", key).strip()


def _locations(posting: dict[str, Any]) -> list[dict[str, Any]]:
    raw = posting.get("jobLocation")
    places = raw if isinstance(raw, list) else [raw] if raw else []
    locations = []
    for place in places:
        if not isinstance(place, dict):
            continue
        address = place.get("address")
        if not isinstance(address, dict):
            address = place
        street = _text(address.get("streetAddress"))
        locality = _text(address.get("addressLocality"))
        region = _text(address.get("addressRegion"))
        country = _text(address.get("addressCountry"))
        city, province = resolve_place(locality, region)
        locations.append(
            {
                "street": street,
                "locality": locality,
                "region": region,
                "country": country,
                "city": city,
                "province": province,
            }
        )
    return locations


def resolve_place(locality: str | None, region: str | None) -> tuple[str | None, str | None]:
    """(city, province) from free-text address parts such as
    locality="Jakarta, Daerah Khusus Ibukota Jakarta, Indonesia", region=None.

    Any part naming one of the 38 provinces (including aliases such as "Jakarta" or
    "Yogyakarta") is treated as the province, never as the city, so "Jakarta" alone gives
    province DKI Jakarta with the city unknown rather than a guessed city. The city is the
    first remaining part; when no province is named, it is inferred from a known city.
    """
    parts = [
        part.strip()
        for text in (region, locality)
        if text
        for part in text.split(",")
        if part.strip() and part.strip().lower() not in _INDONESIA | _NATIONWIDE
    ]
    province = next((p for p in map(canonical_province, parts) if p), None)
    city = canonical_city(next((p for p in parts if canonical_province(p) is None), None))
    if province is None and city is not None:
        province = parse_location(city).province
    return city, province


def _salary(posting: dict[str, Any]) -> tuple[Any, str | None, list[str]]:
    raw = posting.get("baseSalary")
    if not isinstance(raw, dict):
        return (
            evaluate_salary_amounts(None, None, currency=None, period=SalaryPeriod.UNKNOWN),
            None,
            [],
        )
    currency = _text(raw.get("currency"))
    value = raw.get("value")
    unit = None
    minimum = maximum = None
    if isinstance(value, dict):
        unit = _text(value.get("unitText"))
        minimum, maximum = value.get("minValue"), value.get("maxValue")
        if minimum is None and maximum is None:
            minimum = maximum = value.get("value")
    else:
        minimum = maximum = value
    unit = unit or _text(raw.get("unitText"))
    period = _SALARY_UNITS.get((unit or "").upper(), SalaryPeriod.UNKNOWN)

    def number(v: Any) -> int | None:
        try:
            return round(float(str(v).replace(",", ""))) if v not in (None, "") else None
        except ValueError:
            return None

    flags = []
    if currency is None:
        flags.append("SALARY_CURRENCY_MISSING")
    if period is SalaryPeriod.UNKNOWN:
        flags.append("SALARY_PERIOD_MISSING")
    code = currency.strip().upper() if currency else None
    code = _CURRENCY_ALIASES.get(code, code) if code else None
    parsed = evaluate_salary_amounts(number(minimum), number(maximum), currency=code, period=period)
    return parsed, unit, flags + list(parsed.flags)


def _years_of_experience(posting: dict[str, Any]) -> int | None:
    raw = posting.get("experienceRequirements")
    if isinstance(raw, dict) and raw.get("monthsOfExperience") not in (None, ""):
        try:
            return int(float(raw["monthsOfExperience"]) // 12)
        except (TypeError, ValueError):
            return None
    return None


_CREDENTIALS = {
    "high school": EducationLevel.SMA_SMK,
    "associate degree": EducationLevel.DIPLOMA,
    "bachelor degree": EducationLevel.BACHELOR,
    "postgraduate degree": EducationLevel.MASTER,
    "professional certificate": EducationLevel.PROFESSIONAL,
}


def _education(posting: dict[str, Any]) -> EducationLevel:
    raw = posting.get("educationRequirements")
    items = raw if isinstance(raw, list) else [raw]
    for item in items:
        category = _text(item.get("credentialCategory")) if isinstance(item, dict) else _text(item)
        if category:
            return _CREDENTIALS.get(category.lower(), normalize_education(category))
    return EducationLevel.UNKNOWN


def normalize_posting(
    posting: dict[str, Any], *, page_url: str, domain: str, captured_at: datetime, position: int
) -> PostingRow:
    """``position`` distinguishes several JobPosting objects on the same page."""
    title = _text(posting.get("title")) or _text(posting.get("name"))
    organization = _text(posting.get("hiringOrganization"))
    description = description_text(posting.get("description"))
    locations = _locations(posting)
    primary = locations[0] if locations else {}
    countries = {(loc["country"] or "").lower() for loc in locations if loc["country"]}
    salary, salary_unit, salary_flags = _salary(posting)
    employment_raw = posting.get("employmentType")
    employment_first = _text(employment_raw)
    date_posted = _parse_date(posting.get("datePosted"))
    valid_through = _parse_date(posting.get("validThrough"))
    identifier = _identifier(posting.get("identifier"))
    location_type = (_text(posting.get("jobLocationType")) or "").upper()

    row = PostingRow(values={})
    if not title or len(title) < 3:
        row.invalid_reasons.append("missing_title")
    elif _NOT_A_VACANCY.search(title):
        row.invalid_reasons.append("not_a_vacancy")
    employer_key = normalize_for_matching(organization)
    if employer_key in _CONFIDENTIAL_EMPLOYER:
        organization = CONFIDENTIAL_EMPLOYER_NAME
        row.quality_flags.append("EMPLOYER_CONFIDENTIAL")
    elif employer_key in _HOUSEHOLD_EMPLOYER:
        organization = HOUSEHOLD_EMPLOYER_NAME
        row.quality_flags.append("EMPLOYER_HOUSEHOLD")
    if not organization:
        row.invalid_reasons.append("missing_hiring_organization")
    elif _is_placeholder_organization(organization, domain):
        row.invalid_reasons.append("placeholder_hiring_organization")
    if countries and not countries & _INDONESIA:
        row.invalid_reasons.append("location_outside_indonesia")
    if not primary.get("province"):
        row.quality_flags.append("PROVINCE_UNRESOLVED")
    if len(locations) > 1:
        row.quality_flags.append("MULTI_LOCATION")

    captured_date = captured_at.astimezone(timezone.utc).date()
    if date_posted is None:
        row.quality_flags.append(
            "DATE_POSTED_MISSING"
            if posting.get("datePosted") is None
            else "DATE_POSTED_UNPARSEABLE"
        )
    elif date_posted > captured_date + FUTURE_TOLERANCE or date_posted < EARLIEST_PLAUSIBLE_POSTING:
        row.quality_flags.append("DATE_POSTED_IMPLAUSIBLE")
        date_posted = None
    if valid_through is not None and date_posted is not None and valid_through < date_posted:
        row.quality_flags.append("VALID_THROUGH_BEFORE_POSTED")
        valid_through = None
    if valid_through is not None and valid_through < captured_date:
        row.quality_flags.append("EXPIRED_AT_CAPTURE")
    if description is None:
        row.quality_flags.append("DESCRIPTION_MISSING")
    elif len(description) < 100:
        row.quality_flags.append("DESCRIPTION_THIN")
    if salary.status is not SalaryStatus.NOT_DISCLOSED:
        row.quality_flags.extend(salary_flags)

    if location_type == "TELECOMMUTE":
        arrangement = WorkArrangement.REMOTE
    else:
        arrangement = WorkArrangement.UNKNOWN
    canonical_url = canonical_page_url(page_url)
    # Identity is the page URL plus position. Site identifiers are kept as an attribute
    # but not trusted as keys: repost blogs often emit template values such as "1".
    record_key = f"{canonical_url}#{position}"
    disclosed = salary.status is SalaryStatus.DISCLOSED
    comparable = disclosed and salary.currency == "IDR"

    row.values = {
        "source_record_key": record_key,
        "record_key_kind": "page_url",
        "source_domain": domain,
        "canonical_url": canonical_url,
        "posting_position": position,
        "source_identifier": identifier,
        "title": display_title(title, organization) if title else None,
        "source_title": title,
        "title_key": (
            title_key(
                title,
                organization,
                # Street/district names too: SEO pages repeat one title per district.
                (
                    primary.get("city"),
                    primary.get("province"),
                    primary.get("locality"),
                    primary.get("region"),
                    primary.get("street"),
                ),
            )
            if title
            else None
        ),
        "organization": organization,
        "organization_key": organization_key(organization) if organization else None,
        "role_family": classify_role_family(title).value if title else None,
        "city": primary.get("city"),
        "province": primary.get("province"),
        "locality_raw": primary.get("locality"),
        "region_raw": primary.get("region"),
        "country_raw": primary.get("country"),
        "location_count": len(locations),
        "provinces": sorted({loc["province"] for loc in locations if loc["province"]}),
        "employment_type_raw": employment_first,
        "employment_type": _EMPLOYMENT_TYPES.get(
            (employment_first or "").upper().replace("-", "_"), EmploymentType.UNKNOWN
        ).value,
        "work_arrangement": arrangement.value,
        "experience_min_years": _years_of_experience(posting),
        "education_level": _education(posting).value,
        "date_posted": date_posted,
        "valid_through": valid_through,
        "salary_status": salary.status.value,
        "salary_currency": salary.currency if disclosed else None,
        "salary_unit_raw": salary_unit,
        "salary_period": salary.period.value,
        "salary_min": salary.minimum if disclosed else None,
        "salary_max": salary.maximum if disclosed else None,
        "salary_monthly_min": salary.monthly_minimum if comparable else None,
        "salary_monthly_max": salary.monthly_maximum if comparable else None,
        "description_length": len(description) if description else 0,
        "description_sha1": hashlib.sha1(description.encode()).hexdigest() if description else None,
        "skills": extract_skills(description),
        "page_url": page_url,
        "parser_version": PARSER_VERSION,
    }
    return row
