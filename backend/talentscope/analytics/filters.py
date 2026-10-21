"""Filters shared by job search and analytics, so both always describe the same set."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import Select, or_

from talentscope.analytics.salary_rule import comparable_salary
from talentscope.models import Job
from talentscope.vocab import (
    EducationLevel,
    EmploymentType,
    ExperienceBand,
    Freshness,
    RoleFamily,
    WorkArrangement,
)

MAX_QUERY_LENGTH = 100
MAX_QUERY_TERMS = 8
MAX_VALUES_PER_FILTER = 40
MAX_VALUE_LENGTH = 200


class JobFilters(BaseModel):
    """Query-string filters. Repeated parameters select several values (OR within a
    filter); different filters combine with AND."""

    q: str | None = Field(default=None, max_length=MAX_QUERY_LENGTH)
    province: list[str] = Field(default_factory=list, max_length=MAX_VALUES_PER_FILTER)
    city: list[str] = Field(default_factory=list, max_length=MAX_VALUES_PER_FILTER)
    role_family: list[RoleFamily] = Field(default_factory=list)
    employment_type: list[EmploymentType] = Field(default_factory=list)
    work_arrangement: list[WorkArrangement] = Field(default_factory=list)
    education: list[EducationLevel] = Field(default_factory=list)
    experience: list[ExperienceBand] = Field(default_factory=list)
    source: list[str] = Field(default_factory=list, max_length=MAX_VALUES_PER_FILTER)
    # Exact card tags as shown by the source (OR within the filter), unlike `q`, which
    # matches words anywhere in the title, company, location, and tags.
    tag: list[str] = Field(default_factory=list, max_length=MAX_VALUES_PER_FILTER)
    salary_disclosed: bool | None = None
    salary_min: int | None = Field(default=None, ge=0, le=10_000_000_000, description="Monthly IDR")
    salary_max: int | None = Field(default=None, ge=0, le=10_000_000_000, description="Monthly IDR")
    freshness: list[Freshness] = Field(default_factory=list)

    @field_validator("q", "province", "city", "source", "tag", mode="before")
    @classmethod
    def _no_nul_characters(cls, value: object) -> object:
        # PostgreSQL text cannot hold NUL; reject it here instead of failing in the driver.
        values = value if isinstance(value, list) else [value]
        if any(isinstance(v, str) and "\x00" in v for v in values):
            raise ValueError("must not contain NUL characters")
        return value

    @field_validator("province", "city", "source", "tag")
    @classmethod
    def _values_bounded(cls, values: list[str]) -> list[str]:
        if any(len(v) > MAX_VALUE_LENGTH for v in values):
            raise ValueError(f"each value must have at most {MAX_VALUE_LENGTH} characters")
        return values

    @field_validator("q")
    @classmethod
    def _blank_query_is_none(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None

    @model_validator(mode="after")
    def _salary_bounds_ordered(self) -> JobFilters:
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min must not exceed salary_max")
        return self

    def search_terms(self) -> list[str]:
        return self.q.casefold().split()[:MAX_QUERY_TERMS] if self.q else []


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def apply_filters(
    stmt: Select[Any],
    filters: JobFilters,
    *,
    freshness_window_days: int,
    now: datetime | None = None,
) -> Select[Any]:
    for term in filters.search_terms():
        # Every term must appear somewhere in title, company, location, or tags.
        stmt = stmt.where(Job.search_text.ilike(f"%{_escape_like(term)}%", escape="\\"))
    if filters.province:
        stmt = stmt.where(Job.province.in_(filters.province))
    if filters.city:
        stmt = stmt.where(Job.city.in_(filters.city))
    if filters.role_family:
        stmt = stmt.where(Job.role_family.in_([v.value for v in filters.role_family]))
    if filters.employment_type:
        stmt = stmt.where(Job.employment_type.in_([v.value for v in filters.employment_type]))
    if filters.work_arrangement:
        stmt = stmt.where(Job.work_arrangement.in_([v.value for v in filters.work_arrangement]))
    if filters.education:
        stmt = stmt.where(Job.education_level.in_([v.value for v in filters.education]))
    if filters.experience:
        stmt = stmt.where(Job.experience_band.in_([v.value for v in filters.experience]))
    if filters.source:
        stmt = stmt.where(Job.primary_source_id.in_(filters.source))
    if filters.tag:
        stmt = stmt.where(Job.source_tags.overlap(filters.tag))
    if filters.salary_disclosed is not None:
        disclosed = Job.salary_status == "DISCLOSED"
        stmt = stmt.where(disclosed if filters.salary_disclosed else ~disclosed)
    # Salary bounds keep jobs whose monthly range overlaps the requested range. Only
    # comparable salaries (analytics.salary_rule) can satisfy a bound: a USD amount or an
    # implausible "Rp2–897" cannot be compared with a monthly IDR figure, and the jobs a
    # salary filter selects are then exactly the ones salary statistics describe.
    if filters.salary_min is not None or filters.salary_max is not None:
        stmt = stmt.where(comparable_salary(Job))
    if filters.salary_min is not None:
        stmt = stmt.where(Job.salary_monthly_max >= filters.salary_min)
    if filters.salary_max is not None:
        stmt = stmt.where(Job.salary_monthly_min <= filters.salary_max)
    if filters.freshness:
        stmt = stmt.where(
            or_(*(freshness_clause(f, freshness_window_days, now) for f in filters.freshness))
        )
    return stmt


def freshness_clause(freshness: Freshness, window_days: int, now: datetime | None) -> Any:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    expired = Job.expires_at.is_not(None) & (Job.expires_at < now)
    if freshness is Freshness.EXPIRED_BY_SOURCE:
        return expired
    not_expired = or_(Job.expires_at.is_(None), Job.expires_at >= now)
    if freshness is Freshness.POTENTIALLY_ACTIVE:
        return not_expired & (Job.last_seen_at >= cutoff)
    return not_expired & (Job.last_seen_at < cutoff)


def freshness_of(
    last_seen_at: datetime,
    expires_at: datetime | None,
    *,
    window_days: int,
    now: datetime | None = None,
) -> Freshness:
    """Lifecycle label from evidence we have (SRS FR-LIFE-002/003). Presence in the
    database alone never makes a job "active"."""
    now = now or datetime.now(timezone.utc)
    if expires_at is not None and expires_at < now:
        return Freshness.EXPIRED_BY_SOURCE
    if now - last_seen_at <= timedelta(days=window_days):
        return Freshness.POTENTIALLY_ACTIVE
    return Freshness.NOT_SEEN_RECENTLY
