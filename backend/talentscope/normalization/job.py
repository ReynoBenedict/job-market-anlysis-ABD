"""Turn a connector's ``SourceJob`` into the canonical column values of a ``Job``."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from talentscope.ingestion.records import SalaryConvention, SourceJob
from talentscope.normalization.attributes import (
    normalize_education,
    normalize_employment_type,
    parse_experience,
    parse_posting_age,
    split_card_tags,
)
from talentscope.normalization.location import LocationConfidence, parse_location
from talentscope.normalization.role_family import ROLE_TAXONOMY_VERSION, classify_role_family
from talentscope.normalization.salary import SalaryParse, evaluate_salary_amounts, parse_salary
from talentscope.normalization.text import clean_text, normalize_for_matching
from talentscope.vocab import RoleFamily, SalaryStatus, WorkArrangement

NORMALIZATION_VERSION = f"1.3+roles-{ROLE_TAXONOMY_VERSION}"

FLAG_LOCATION_UNRESOLVED = "LOCATION_UNRESOLVED"
FLAG_ROLE_UNCLASSIFIED = "ROLE_UNCLASSIFIED"
FLAG_TAGS_TRUNCATED = "TAGS_TRUNCATED"
FLAG_INVALID_SOURCE_URL = "INVALID_SOURCE_URL"
FLAG_POSTING_AGE_APPROXIMATE = "POSTING_AGE_APPROXIMATE"
FLAG_SALARY_PERIOD_ASSUMED = "SALARY_PERIOD_ASSUMED"

_WORK_ARRANGEMENT_TEXT = {
    "remote": WorkArrangement.REMOTE,
    "hybrid": WorkArrangement.HYBRID,
    "on site": WorkArrangement.ONSITE,
    "onsite": WorkArrangement.ONSITE,
    "in office": WorkArrangement.ONSITE,
}


class InvalidSourceJob(ValueError):
    """A record that cannot become a canonical job (e.g. it has no title)."""


@dataclass(frozen=True)
class NormalizedJob:
    values: dict[str, Any]
    fingerprint: str
    content_hash: str


def validated_url(value: str | None) -> str | None:
    """Return the URL if it is an absolute http(s) URL with a host, else None."""
    url = clean_text(value)
    if url is None:
        return None
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    return url


def job_fingerprint(title: str, company: str | None, place: str | None) -> str:
    key = "|".join(normalize_for_matching(part) for part in (title, company, place))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def content_hash(raw_fields: dict[str, Any]) -> str:
    payload = json.dumps(raw_fields, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _salary(job: SourceJob, convention: SalaryConvention | None) -> SalaryParse:
    if job.structured_salary is not None:
        structured = job.structured_salary
        return evaluate_salary_amounts(
            structured.minimum,
            structured.maximum,
            currency=structured.currency,
            period=structured.period,
        )
    return parse_salary(
        job.salary_text,
        default_currency=convention.currency if convention else None,
        assumed_period=convention.period if convention else None,
    )


def normalize_source_job(
    job: SourceJob, *, observed_at: datetime, salary_convention: SalaryConvention | None = None
) -> NormalizedJob:
    title = clean_text(job.title)
    if title is None:
        raise InvalidSourceJob("record has no job title")

    company = clean_text(job.company_name)
    location_text = clean_text(job.location_text)
    location = parse_location(location_text)
    tags = split_card_tags(job.tags)
    salary = _salary(job, salary_convention)
    experience = parse_experience(job.experience_text)
    posting = parse_posting_age(job.posted_text)
    role_family = classify_role_family(title)

    arrangement, evidence = tags.work_arrangement, tags.work_arrangement_evidence
    explicit = _WORK_ARRANGEMENT_TEXT.get(normalize_for_matching(job.work_arrangement_text))
    if explicit is not None:
        arrangement, evidence = explicit, clean_text(job.work_arrangement_text)
    elif arrangement is WorkArrangement.UNKNOWN and location.is_remote:
        arrangement, evidence = WorkArrangement.REMOTE, location_text

    flags = list(salary.flags)
    if salary.period_assumed:
        flags.append(FLAG_SALARY_PERIOD_ASSUMED)
    if location.confidence is LocationConfidence.UNKNOWN and not location.is_remote:
        flags.append(FLAG_LOCATION_UNRESOLVED)
    if role_family is RoleFamily.OTHER:
        flags.append(FLAG_ROLE_UNCLASSIFIED)
    if tags.hidden_count:
        flags.append(FLAG_TAGS_TRUNCATED)
    if posting.approximate:
        flags.append(FLAG_POSTING_AGE_APPROXIMATE)
    source_url = validated_url(job.source_url)
    if job.source_url and source_url is None:
        flags.append(FLAG_INVALID_SOURCE_URL)

    disclosed = salary.status is SalaryStatus.DISCLOSED
    values: dict[str, Any] = {
        "title": title,
        "role_family": role_family.value,
        "company_name": company,
        "location_text": location_text,
        "city": location.city,
        "province": location.province,
        "location_confidence": location.confidence.value,
        "employment_type_text": clean_text(job.employment_type_text),
        "employment_type": normalize_employment_type(job.employment_type_text).value,
        "work_arrangement": arrangement.value,
        "work_arrangement_evidence": evidence,
        "experience_text": clean_text(job.experience_text),
        "experience_min_years": experience.min_years,
        "experience_max_years": experience.max_years,
        "experience_band": experience.band.value,
        "education_text": clean_text(job.education_text),
        "education_level": normalize_education(job.education_text).value,
        "salary_text": clean_text(job.salary_text),
        "salary_status": salary.status.value,
        "salary_min": salary.minimum if disclosed else None,
        "salary_max": salary.maximum if disclosed else None,
        "salary_currency": salary.currency if disclosed else None,
        "salary_period": salary.period.value,
        "salary_period_assumed": salary.period_assumed,
        "salary_monthly_min": salary.monthly_minimum if disclosed else None,
        "salary_monthly_max": salary.monthly_maximum if disclosed else None,
        "source_tags": list(tags.skills),
        "hidden_tag_count": tags.hidden_count,
        "description": clean_text(job.description),
        "posted_text": clean_text(job.posted_text),
        "posted_age_days": posting.days,
        "is_urgent": posting.is_urgent,
        "published_at": job.published_at,
        "expires_at": job.expires_at,
        "source_url": source_url,
        "quality_flags": sorted(set(flags)),
        "normalization_version": NORMALIZATION_VERSION,
        "search_text": " ".join(
            part for part in (title, company, location_text, *tags.skills) if part
        ).casefold(),
    }
    place = location.city or location.province
    return NormalizedJob(
        values=values,
        fingerprint=job_fingerprint(title, company, place),
        content_hash=content_hash(dict(job.raw_fields)),
    )
