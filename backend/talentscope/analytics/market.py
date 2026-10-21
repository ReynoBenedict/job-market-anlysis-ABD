"""Aggregate counts over canonical jobs. Every result carries its denominator."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from talentscope.analytics.filters import JobFilters, apply_filters
from talentscope.models import Job, Source, SourceRecord
from talentscope.vocab import (
    EducationLevel,
    EmploymentType,
    ExperienceBand,
    LabelledEnum,
    RoleFamily,
    SalaryStatus,
    WorkArrangement,
)


class Dimension(str, Enum):
    PROVINCE = "province"
    CITY = "city"
    ROLE_FAMILY = "role_family"
    EMPLOYMENT_TYPE = "employment_type"
    WORK_ARRANGEMENT = "work_arrangement"
    EDUCATION = "education"
    EXPERIENCE = "experience"
    COMPANY = "company"
    TITLE = "title"
    SOURCE = "source"


def _enum_labeller(enum: type[LabelledEnum]) -> Callable[[Any], str]:
    return lambda code: enum(code).label


def _identity_label(value: Any) -> str:
    return str(value) if value is not None else "Tidak dicantumkan"


@dataclass(frozen=True)
class DimensionSpec:
    column: str  # column on the jobs table
    label: Callable[[Any], str]


DIMENSIONS: dict[Dimension, DimensionSpec] = {
    Dimension.PROVINCE: DimensionSpec("province", _identity_label),
    Dimension.CITY: DimensionSpec("city", _identity_label),
    Dimension.ROLE_FAMILY: DimensionSpec("role_family", _enum_labeller(RoleFamily)),
    Dimension.EMPLOYMENT_TYPE: DimensionSpec("employment_type", _enum_labeller(EmploymentType)),
    Dimension.WORK_ARRANGEMENT: DimensionSpec("work_arrangement", _enum_labeller(WorkArrangement)),
    Dimension.EDUCATION: DimensionSpec("education_level", _enum_labeller(EducationLevel)),
    Dimension.EXPERIENCE: DimensionSpec("experience_band", _enum_labeller(ExperienceBand)),
    Dimension.COMPANY: DimensionSpec("company_name", _identity_label),
    Dimension.TITLE: DimensionSpec("title", _identity_label),
    Dimension.SOURCE: DimensionSpec("primary_source_id", _identity_label),
}


# Host of an absolute URL (optional user-info skipped, port dropped). Written without
# backslashes so the pattern reads the same in Python and PostgreSQL.
_URL_HOST_PATTERN = "^[A-Za-z][A-Za-z0-9+.-]*://(?:[^/?#@]*@)?([^/?#:]+)"


def publisher_site(source_url: Any) -> Any:
    """Site that published a listing: lower-cased host of ``source_url`` without a leading
    "www.". NULL when the job has no URL (e.g. the historical snapshot). This is distinct
    from ``source``, which is the ingestion dataset (e.g. one web-archive source spans
    many publisher sites)."""
    host = func.lower(func.substring(source_url, _URL_HOST_PATTERN))
    return func.regexp_replace(host, "^www[.]", "")


def labeller_for(session: Session, dimension: Dimension) -> Callable[[Any], str]:
    if dimension is Dimension.SOURCE:
        names = dict(session.execute(select(Source.id, Source.name)).tuples().all())
        return lambda value: names.get(value, str(value))
    return DIMENSIONS[dimension].label


@dataclass(frozen=True)
class BreakdownRow:
    key: str | None
    label: str
    count: int
    share: float


@dataclass(frozen=True)
class Breakdown:
    dimension: Dimension
    total: int
    rows: list[BreakdownRow]
    other_count: int  # jobs in categories beyond the returned limit
    distinct_values: int


def breakdown(
    session: Session,
    dimension: Dimension,
    filters: JobFilters,
    *,
    limit: int,
    freshness_window_days: int,
) -> Breakdown:
    filtered = apply_filters(
        select(Job), filters, freshness_window_days=freshness_window_days
    ).subquery()
    column = filtered.c[DIMENSIONS[dimension].column]
    grouped = session.execute(
        select(column, func.count().label("n"))
        .group_by(column)
        .order_by(func.count().desc(), column)
    ).all()
    total = sum(n for _, n in grouped)

    labels = labeller_for(session, dimension)
    rows = [
        BreakdownRow(key, labels(key), n, n / total if total else 0.0) for key, n in grouped[:limit]
    ]
    return Breakdown(dimension, total, rows, sum(n for _, n in grouped[limit:]), len(grouped))


@dataclass(frozen=True)
class Overview:
    total_jobs: int
    total_source_records: int
    companies: int
    cities: int
    provinces: int
    sources_with_jobs: int
    publisher_sites: int
    salary_disclosed: int
    remote_or_hybrid: int
    observed_from: datetime | None
    observed_to: datetime | None


def overview(session: Session, filters: JobFilters, *, freshness_window_days: int) -> Overview:
    filtered = apply_filters(
        select(Job), filters, freshness_window_days=freshness_window_days
    ).subquery()
    row = session.execute(
        select(
            func.count(),
            func.count(func.distinct(func.lower(filtered.c.company_name))),
            func.count(func.distinct(filtered.c.city)),
            func.count(func.distinct(filtered.c.province)),
            func.count(func.distinct(filtered.c.primary_source_id)),
            func.count(func.distinct(publisher_site(filtered.c.source_url))),
            func.count().filter(filtered.c.salary_status == SalaryStatus.DISCLOSED.value),
            func.count().filter(filtered.c.work_arrangement.in_(["REMOTE", "HYBRID"])),
            func.min(filtered.c.last_seen_at),
            func.max(filtered.c.last_seen_at),
        )
    ).one()
    records = session.scalar(
        select(func.count())
        .select_from(SourceRecord)
        .where(SourceRecord.job_id.in_(select(filtered.c.id)))
    )
    return Overview(
        total_jobs=row[0],
        total_source_records=records or 0,
        companies=row[1],
        cities=row[2],
        provinces=row[3],
        sources_with_jobs=row[4],
        publisher_sites=row[5],
        salary_disclosed=row[6],
        remote_or_hybrid=row[7],
        observed_from=row[8],
        observed_to=row[9],
    )
