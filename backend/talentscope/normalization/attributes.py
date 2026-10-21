"""Normalization of categorical job attributes: employment type, experience, education,
work arrangement, card tags, and relative posting age."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from talentscope.normalization.text import clean_text, normalize_for_matching
from talentscope.vocab import EducationLevel, EmploymentType, ExperienceBand, WorkArrangement

# Checked in order; the first keyword contained in the normalized label wins. Indonesian
# and English variants are both listed because boards mix the two.
_EMPLOYMENT_KEYWORDS: tuple[tuple[str, EmploymentType], ...] = (
    ("paruh waktu", EmploymentType.PART_TIME),
    ("part time", EmploymentType.PART_TIME),
    ("penuh waktu", EmploymentType.FULL_TIME),
    ("full time", EmploymentType.FULL_TIME),
    ("permanent", EmploymentType.FULL_TIME),
    ("tetap", EmploymentType.FULL_TIME),
    ("pemagangan", EmploymentType.APPRENTICESHIP),
    ("apprentice", EmploymentType.APPRENTICESHIP),
    ("magang", EmploymentType.INTERNSHIP),
    ("intern", EmploymentType.INTERNSHIP),
    ("kontrak", EmploymentType.CONTRACT),
    ("contract", EmploymentType.CONTRACT),
    ("pkwt", EmploymentType.CONTRACT),
    ("freelance", EmploymentType.FREELANCE),
    ("lepas", EmploymentType.FREELANCE),
    ("temporary", EmploymentType.TEMPORARY),
    ("sementara", EmploymentType.TEMPORARY),
    ("project", EmploymentType.PROJECT_BASED),
    ("proyek", EmploymentType.PROJECT_BASED),
    ("volunteer", EmploymentType.VOLUNTEER),
    ("sukarela", EmploymentType.VOLUNTEER),
)


def normalize_employment_type(value: object) -> EmploymentType:
    key = normalize_for_matching(clean_text(value))
    for keyword, employment_type in _EMPLOYMENT_KEYWORDS:
        if keyword in key:
            return employment_type
    return EmploymentType.UNKNOWN


@dataclass(frozen=True)
class ExperienceParse:
    min_years: int | None
    max_years: int | None
    band: ExperienceBand


_RANGE = re.compile(r"(\d+)\s*[-–—]\s*(\d+)")
_AT_LEAST = re.compile(r"(?:lebih dari|minimal|min\.?|at least|more than|>)\s*(\d+)|(\d+)\s*\+")
_LESS_THAN = re.compile(r"(?:kurang dari|less than|<)\s*(\d+)")
_SINGLE = re.compile(r"(\d+)\s*(?:tahun|thn|years?|yrs?)")


def _band_for(min_years: int | None, max_years: int | None) -> ExperienceBand:
    """Bucket by the lower bound, which is what a job seeker must satisfy."""
    if min_years is None:
        return (
            ExperienceBand.UNDER_1
            if max_years is not None and max_years <= 1
            else ExperienceBand.UNKNOWN
        )
    if min_years < 1:
        return ExperienceBand.UNDER_1
    if min_years < 3:
        return ExperienceBand.Y1_3
    if min_years < 5:
        return ExperienceBand.Y3_5
    if min_years < 10:
        return ExperienceBand.Y5_10
    return ExperienceBand.OVER_10


def parse_experience(value: object) -> ExperienceParse:
    text = clean_text(value)
    if text is None:
        return ExperienceParse(None, None, ExperienceBand.UNKNOWN)
    lowered = text.casefold()
    if any(
        term in lowered
        for term in ("fresh graduate", "lulusan baru", "tanpa pengalaman", "no experience")
    ):
        return ExperienceParse(0, 0, ExperienceBand.UNDER_1)
    if match := _RANGE.search(lowered):
        low, high = sorted((int(match.group(1)), int(match.group(2))))
        return ExperienceParse(low, high, _band_for(low, high))
    if match := _LESS_THAN.search(lowered):
        high = int(match.group(1))
        return ExperienceParse(0, high, _band_for(0, high))
    if match := _AT_LEAST.search(lowered):
        low = int(match.group(1) or match.group(2))
        # "Lebih dari 10 tahun" states a strict lower bound; we keep the stated number
        # rather than inventing "11", and leave the upper bound open.
        return ExperienceParse(low, None, _band_for(low, None))
    if match := _SINGLE.search(lowered):
        years = int(match.group(1))
        return ExperienceParse(years, years, _band_for(years, years))
    return ExperienceParse(None, None, ExperienceBand.UNKNOWN)


_EDUCATION_KEYWORDS: tuple[tuple[str, EducationLevel], ...] = (
    ("doktor", EducationLevel.DOCTORATE),
    ("s3", EducationLevel.DOCTORATE),
    ("phd", EducationLevel.DOCTORATE),
    ("magister", EducationLevel.MASTER),
    ("s2", EducationLevel.MASTER),
    ("master", EducationLevel.MASTER),
    ("profesi", EducationLevel.PROFESSIONAL),
    ("sarjana", EducationLevel.BACHELOR),
    ("s1", EducationLevel.BACHELOR),
    ("bachelor", EducationLevel.BACHELOR),
    ("diploma", EducationLevel.DIPLOMA),
    ("d3", EducationLevel.DIPLOMA),
    ("d4", EducationLevel.DIPLOMA),
    ("d1", EducationLevel.DIPLOMA),
    ("sma", EducationLevel.SMA_SMK),
    ("smk", EducationLevel.SMA_SMK),
    ("slta", EducationLevel.SMA_SMK),
    ("high school", EducationLevel.SMA_SMK),
    ("smp", EducationLevel.SMP),
    ("sltp", EducationLevel.SMP),
    ("sd", EducationLevel.SD),
)


def normalize_education(value: object) -> EducationLevel:
    tokens = normalize_for_matching(clean_text(value))
    padded = f" {tokens} "
    for keyword, level in _EDUCATION_KEYWORDS:
        # Short codes such as "sd" or "s1" must match whole words, not substrings.
        if f" {keyword} " in padded or (len(keyword) > 3 and keyword in tokens):
            return level
    return EducationLevel.UNKNOWN


_HIDDEN_TAG_COUNT = re.compile(r"^\+(\d+)$")
_TAG_ARRANGEMENTS = {
    "hybrid": WorkArrangement.HYBRID,
    "remote": WorkArrangement.REMOTE,
    "remote dari rumah": WorkArrangement.REMOTE,
    "dari rumah": WorkArrangement.REMOTE,
    "work from home": WorkArrangement.REMOTE,
    "wfh": WorkArrangement.REMOTE,
    "on site": WorkArrangement.ONSITE,
    "onsite": WorkArrangement.ONSITE,
    "wfo": WorkArrangement.ONSITE,
}
# Badges that describe the listing rather than the job.
_NON_SKILL_TAGS = frozenset({"perusahaan premium", "urgent", "premium"})


@dataclass(frozen=True)
class CardTags:
    """Tags shown on a job-board card, split by meaning.

    Card tags are a truncated preview ("+5" means five more were hidden), so they are
    a weak signal of skills and must never be presented as a job's full requirements.
    """

    skills: tuple[str, ...] = ()
    hidden_count: int = 0
    work_arrangement: WorkArrangement = WorkArrangement.UNKNOWN
    work_arrangement_evidence: str | None = None
    ignored: tuple[str, ...] = field(default=())


def split_card_tags(tags: list[str] | tuple[str, ...]) -> CardTags:
    skills: list[str] = []
    ignored: list[str] = []
    hidden = 0
    arrangement, evidence = WorkArrangement.UNKNOWN, None
    for raw_tag in tags:
        tag = clean_text(raw_tag)
        if tag is None:
            continue
        if match := _HIDDEN_TAG_COUNT.match(tag):
            hidden += int(match.group(1))
            continue
        key = normalize_for_matching(tag)
        if key in _TAG_ARRANGEMENTS:
            arrangement, evidence = _TAG_ARRANGEMENTS[key], tag
            continue
        if key in _NON_SKILL_TAGS:
            ignored.append(tag)
            continue
        if tag not in skills:
            skills.append(tag)
    return CardTags(tuple(skills), hidden, arrangement, evidence, tuple(ignored))


@dataclass(frozen=True)
class PostingAge:
    """Age of a listing as stated relative to the moment it was observed.

    Relative strings such as "3 hari yang lalu" cannot be turned into a publication
    date unless the observation time is known precisely, so only the age is stored.
    """

    days: int | None
    is_urgent: bool
    approximate: bool


_AGE_UNITS_IN_DAYS = {"menit": 0, "jam": 0, "hari": 1, "minggu": 7, "bulan": 30, "tahun": 365}
_AGE = re.compile(r"(\d+)\s*(menit|jam|hari|minggu|bulan|tahun)")


def parse_posting_age(value: object) -> PostingAge:
    text = clean_text(value)
    if text is None:
        return PostingAge(None, False, False)
    lowered = text.casefold()
    # The legacy scraper concatenated the "Urgent" badge into this field ("UrgentKemarin").
    is_urgent = lowered.startswith("urgent")
    if is_urgent:
        lowered = lowered.removeprefix("urgent").strip()
    if lowered in ("baru saja", "hari ini"):
        return PostingAge(0, is_urgent, False)
    if lowered == "kemarin":
        return PostingAge(1, is_urgent, False)
    if match := _AGE.search(lowered):
        amount, unit = int(match.group(1)), match.group(2)
        # Weeks, months, and years are rounded by the source and treated as approximate.
        return PostingAge(
            amount * _AGE_UNITS_IN_DAYS[unit], is_urgent, unit in ("minggu", "bulan", "tahun")
        )
    return PostingAge(None, is_urgent, False)
