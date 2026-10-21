"""Salary statistics (SRS FR-SAL-003..008).

Eligible records are exactly those with a comparable salary as defined in
``analytics.salary_rule`` (disclosed, IDR, monthly equivalent known, ordered range,
monthly midpoint at least Rp500,000). Each record contributes one value, the midpoint
of its monthly range, so wide ranges do not count twice. Flagged high outliers and wide
ranges are included and counted, never silently removed; medians and quartiles are
robust to them. Records failing only the plausibility part of the rule are counted in
``excluded_implausible`` so the exclusion is disclosed.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from talentscope.analytics.filters import JobFilters, apply_filters
from talentscope.analytics.market import DIMENSIONS, Dimension, labeller_for
from talentscope.analytics.salary_rule import (
    comparable_salary,
    monthly_idr_recorded,
    monthly_midpoint,
)
from talentscope.models import Job
from talentscope.normalization.salary import FLAG_HIGH_OUTLIER, FLAG_LOW_OUTLIER, FLAG_WIDE_RANGE

# Below this many records a group gets no percentiles at all.
MIN_RECORDS_FOR_STATISTICS = 5
# Below this many records statistics are shown with a "small sample" warning.
SMALL_SAMPLE_THRESHOLD = 20
HISTOGRAM_BIN_WIDTH = 2_000_000
HISTOGRAM_UPPER_EDGE = 30_000_000

PERCENTILES = (0.10, 0.25, 0.50, 0.75, 0.90)
REPORTED_FLAGS = (FLAG_WIDE_RANGE, FLAG_HIGH_OUTLIER, FLAG_LOW_OUTLIER)


@dataclass(frozen=True)
class SalaryOverview:
    total_jobs: int
    status_counts: dict[str, int]
    eligible: int
    excluded_implausible: int
    period_assumed: int
    percentiles: dict[str, float] | None
    # Medians of the range bounds of eligible records (lower bounds / upper bounds).
    median_min: float | None
    median_max: float | None
    histogram: list[tuple[int, int | None, int]]  # (lower, upper or None for open, count)
    flag_counts: dict[str, int]


def overview(
    session: Session, filters: JobFilters, *, freshness_window_days: int
) -> SalaryOverview:
    filtered = apply_filters(
        select(Job), filters, freshness_window_days=freshness_window_days
    ).subquery()
    status_counts = dict(
        session.execute(
            select(filtered.c.salary_status, func.count()).group_by(filtered.c.salary_status)
        )
        .tuples()
        .all()
    )
    eligible = comparable_salary(filtered.c)
    midpoint = monthly_midpoint(filtered.c)
    excluded = session.scalar(
        select(func.count()).where(monthly_idr_recorded(filtered.c) & ~eligible)
    )
    stats = session.execute(
        select(
            func.count(),
            func.count().filter(filtered.c.salary_period_assumed.is_(True)),
            *[func.percentile_cont(p).within_group(midpoint) for p in PERCENTILES],
            func.percentile_cont(0.5).within_group(filtered.c.salary_monthly_min),
            func.percentile_cont(0.5).within_group(filtered.c.salary_monthly_max),
            *[func.count().filter(filtered.c.quality_flags.any(flag)) for flag in REPORTED_FLAGS],
        ).where(eligible)
    ).one()
    n = stats[0]
    enough = n >= MIN_RECORDS_FOR_STATISTICS

    bucket = func.least(
        func.floor(midpoint / HISTOGRAM_BIN_WIDTH), HISTOGRAM_UPPER_EDGE // HISTOGRAM_BIN_WIDTH
    )
    counts = dict(
        session.execute(select(bucket, func.count()).where(eligible).group_by(bucket))
        .tuples()
        .all()
    )
    last_bin = HISTOGRAM_UPPER_EDGE // HISTOGRAM_BIN_WIDTH
    histogram = (
        [
            (
                i * HISTOGRAM_BIN_WIDTH,
                None if i == last_bin else (i + 1) * HISTOGRAM_BIN_WIDTH,
                int(counts.get(i, 0)),
            )
            for i in range(last_bin + 1)
        ]
        if n
        else []
    )
    return SalaryOverview(
        total_jobs=sum(status_counts.values()),
        status_counts=status_counts,
        eligible=n,
        excluded_implausible=excluded or 0,
        period_assumed=stats[1],
        percentiles={
            f"p{int(p * 100)}": float(v) for p, v in zip(PERCENTILES, stats[2:7], strict=True)
        }
        if enough
        else None,
        median_min=float(stats[7]) if enough else None,
        median_max=float(stats[8]) if enough else None,
        histogram=histogram,
        flag_counts=dict(zip(REPORTED_FLAGS, stats[9:], strict=True)),
    )


@dataclass(frozen=True)
class SalaryGroup:
    key: str | None
    label: str
    n: int
    jobs_in_group: int
    p25: float | None
    median: float | None
    p75: float | None
    small_sample: bool


def compare(
    session: Session, by: Dimension, filters: JobFilters, *, limit: int, freshness_window_days: int
) -> list[SalaryGroup]:
    filtered = apply_filters(
        select(Job), filters, freshness_window_days=freshness_window_days
    ).subquery()
    column = filtered.c[DIMENSIONS[by].column]
    label = labeller_for(session, by)
    eligible = comparable_salary(filtered.c)
    midpoint = monthly_midpoint(filtered.c)
    rows = session.execute(
        select(
            column,
            func.count().filter(eligible),
            func.count(),
            func.percentile_cont(0.25).within_group(midpoint).filter(eligible),
            func.percentile_cont(0.50).within_group(midpoint).filter(eligible),
            func.percentile_cont(0.75).within_group(midpoint).filter(eligible),
        )
        .group_by(column)
        .order_by(func.count().filter(eligible).desc(), column)
        .limit(limit)
    ).all()
    groups = []
    for key, n, jobs, p25, p50, p75 in rows:
        enough = n >= MIN_RECORDS_FOR_STATISTICS
        groups.append(
            SalaryGroup(
                key=key,
                label=label(key),
                n=n,
                jobs_in_group=jobs,
                p25=float(p25) if enough else None,
                median=float(p50) if enough else None,
                p75=float(p75) if enough else None,
                small_sample=n < SMALL_SAMPLE_THRESHOLD,
            )
        )
    return groups
