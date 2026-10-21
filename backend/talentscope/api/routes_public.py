"""Public, read-only endpoints under /api/v1."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import func, select

from talentscope.analytics import market, salary, tags
from talentscope.analytics.filters import JobFilters, freshness_clause
from talentscope.analytics.jobs import JobSort, get_job, search_jobs
from talentscope.analytics.market import Dimension
from talentscope.analytics.salary_rule import (
    COMPARABLE_CURRENCY,
    MIN_MONTHLY_MIDPOINT,
    comparable_salary,
)
from talentscope.api.deps import SessionDep, SettingsDep
from talentscope.api.errors import ApiError
from talentscope.api.schemas import (
    BreakdownOut,
    BreakdownRowOut,
    FilterOption,
    FilterOptions,
    HistogramBin,
    JobDetail,
    JobSummary,
    MarketOverview,
    Page,
    SalaryComparisonOut,
    SalaryGroupOut,
    SalaryOverviewOut,
    SourceCoverage,
    TagStatsOut,
)
from talentscope.api.scope import dataset_scope
from talentscope.models import IngestionRun, Job, Source
from talentscope.vocab import (
    EducationLevel,
    EmploymentType,
    ExperienceBand,
    Freshness,
    RoleFamily,
    RunStatus,
    SalaryStatus,
    WorkArrangement,
)

router = APIRouter(prefix="/api/v1")


def job_filters(
    q: Annotated[
        str | None,
        Query(max_length=100, description="Words to find in title, company, location, tags"),
    ] = None,
    province: Annotated[list[str], Query()] = [],  # noqa: B006  (FastAPI copies defaults)
    city: Annotated[list[str], Query()] = [],  # noqa: B006
    role_family: Annotated[list[RoleFamily], Query()] = [],  # noqa: B006
    employment_type: Annotated[list[EmploymentType], Query()] = [],  # noqa: B006
    work_arrangement: Annotated[list[WorkArrangement], Query()] = [],  # noqa: B006
    education: Annotated[list[EducationLevel], Query()] = [],  # noqa: B006
    experience: Annotated[list[ExperienceBand], Query()] = [],  # noqa: B006
    source: Annotated[list[str], Query()] = [],  # noqa: B006
    tag: Annotated[
        list[str], Query(description="Exact source card tag, e.g. from /skills/source-tags")
    ] = [],  # noqa: B006
    salary_disclosed: bool | None = None,
    salary_min: Annotated[int | None, Query(ge=0, description="Monthly IDR lower bound")] = None,
    salary_max: Annotated[int | None, Query(ge=0, description="Monthly IDR upper bound")] = None,
    freshness: Annotated[list[Freshness], Query()] = [],  # noqa: B006
) -> JobFilters:
    """Shared filter parameters; identical for search and every analytics endpoint."""
    try:
        return JobFilters(
            q=q,
            province=province,
            city=city,
            role_family=role_family,
            employment_type=employment_type,
            work_arrangement=work_arrangement,
            education=education,
            experience=experience,
            source=source,
            tag=tag,
            salary_disclosed=salary_disclosed,
            salary_min=salary_min,
            salary_max=salary_max,
            freshness=freshness,
        )
    except ValidationError as exc:
        # Same location shape as FastAPI's own errors, so `field` names the parameter.
        errors = [{**err, "loc": ("query", *err["loc"])} for err in exc.errors(include_url=False)]
        raise RequestValidationError(errors) from exc


FiltersDep = Annotated[JobFilters, Depends(job_filters)]
MAX_PAGE_SIZE = 50
MAX_BREAKDOWN_ROWS = 50


@router.get("/jobs", response_model=Page[JobSummary], tags=["jobs"])
def list_jobs(
    session: SessionDep,
    settings: SettingsDep,
    filters: FiltersDep,
    sort: JobSort = JobSort.NEWEST,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
) -> Page[JobSummary]:
    """Search canonical jobs. `q` matches every word against title, company, location,
    and card tags. Sorting always ends with the job ID, so pages are stable."""
    if sort is JobSort.RELEVANCE and not filters.q:
        sort = JobSort.NEWEST
    window = settings.freshness_window_days
    rows, total = search_jobs(
        session, filters, sort=sort, page=page, page_size=page_size, freshness_window_days=window
    )
    items = [JobSummary.from_job(job, freshness_window_days=window) for job in rows]
    return Page[JobSummary].build(items, page=page, page_size=page_size, total=total)


@router.get("/jobs/{job_id}", response_model=JobDetail, tags=["jobs"])
def job_detail(job_id: uuid.UUID, session: SessionDep, settings: SettingsDep) -> JobDetail:
    job = get_job(session, job_id)
    if job is None:
        raise ApiError(404, "job_not_found", "Lowongan tidak ditemukan.")
    source_ids = {record.source_id for record in job.source_records} | {job.primary_source_id}
    sources = {s.id: s for s in session.scalars(select(Source).where(Source.id.in_(source_ids)))}
    return JobDetail.build(
        job, freshness_window_days=settings.freshness_window_days, sources=sources
    )


@router.get("/filters", response_model=FilterOptions, tags=["jobs"])
def filter_options(session: SessionDep, settings: SettingsDep) -> FilterOptions:
    """Values present in the data for each filter, with job counts (the 200 most common
    per filter; `city` has more). `salary_monthly_range` spans comparable salaries only."""
    window, everything = settings.freshness_window_days, JobFilters()

    def options(dimension: Dimension, limit: int = 200) -> list[FilterOption]:
        result = market.breakdown(
            session, dimension, everything, limit=limit, freshness_window_days=window
        )
        return [
            FilterOption(value=row.key, label=row.label, count=row.count)
            for row in result.rows
            if row.key is not None
        ]

    bounds = session.execute(
        select(func.min(Job.salary_monthly_min), func.max(Job.salary_monthly_max)).where(
            comparable_salary(Job)
        )
    ).one()
    return FilterOptions(
        total=session.scalar(select(func.count()).select_from(Job)) or 0,
        province=options(Dimension.PROVINCE),
        city=options(Dimension.CITY),
        role_family=options(Dimension.ROLE_FAMILY),
        employment_type=options(Dimension.EMPLOYMENT_TYPE),
        work_arrangement=options(Dimension.WORK_ARRANGEMENT),
        education=options(Dimension.EDUCATION),
        experience=options(Dimension.EXPERIENCE),
        source=options(Dimension.SOURCE),
        freshness=[
            FilterOption(
                value=status.value,
                label=status.label,
                count=session.scalar(
                    select(func.count()).where(freshness_clause(status, window, None))
                )
                or 0,
            )
            for status in Freshness
        ],
        salary_monthly_range=(int(bounds[0]), int(bounds[1])) if bounds[0] is not None else None,
    )


@router.get("/market/overview", response_model=MarketOverview, tags=["market"])
def market_overview(
    session: SessionDep, settings: SettingsDep, filters: FiltersDep
) -> MarketOverview:
    window = settings.freshness_window_days
    result = market.overview(session, filters, freshness_window_days=window)
    return MarketOverview(
        total_jobs=result.total_jobs,
        total_source_records=result.total_source_records,
        companies=result.companies,
        cities=result.cities,
        provinces=result.provinces,
        publisher_sites=result.publisher_sites,
        salary_disclosed=result.salary_disclosed,
        salary_disclosed_share=result.salary_disclosed / result.total_jobs
        if result.total_jobs
        else 0.0,
        remote_or_hybrid=result.remote_or_hybrid,
        scope=dataset_scope(session, filters, freshness_window_days=window),
    )


@router.get("/market/breakdown/{dimension}", response_model=BreakdownOut, tags=["market"])
def market_breakdown(
    dimension: Dimension,
    session: SessionDep,
    settings: SettingsDep,
    filters: FiltersDep,
    limit: Annotated[int, Query(ge=1, le=MAX_BREAKDOWN_ROWS)] = 10,
) -> BreakdownOut:
    """Job counts per category. `other_count` covers categories beyond `limit`."""
    result = market.breakdown(
        session,
        dimension,
        filters,
        limit=limit,
        freshness_window_days=settings.freshness_window_days,
    )
    return BreakdownOut(
        dimension=dimension.value,
        total=result.total,
        distinct_values=result.distinct_values,
        other_count=result.other_count,
        rows=[
            BreakdownRowOut(key=r.key, label=r.label, count=r.count, share=r.share)
            for r in result.rows
        ],
    )


@router.get("/salaries/overview", response_model=SalaryOverviewOut, tags=["salaries"])
def salary_overview(
    session: SessionDep, settings: SettingsDep, filters: FiltersDep
) -> SalaryOverviewOut:
    """Distribution of monthly IDR salary midpoints for jobs with a comparable salary
    (analytics.salary_rule); `excluded_implausible` counts disclosed salaries left out."""
    window = settings.freshness_window_days
    result = salary.overview(session, filters, freshness_window_days=window)
    return SalaryOverviewOut(
        total_jobs=result.total_jobs,
        status_counts=[
            FilterOption(value=code, label=SalaryStatus(code).label, count=count)
            for code, count in sorted(result.status_counts.items(), key=lambda kv: -kv[1])
        ],
        eligible=result.eligible,
        eligible_share=result.eligible / result.total_jobs if result.total_jobs else 0.0,
        excluded_implausible=result.excluded_implausible,
        min_monthly_midpoint=MIN_MONTHLY_MIDPOINT,
        period_assumed=result.period_assumed,
        min_records_for_statistics=salary.MIN_RECORDS_FOR_STATISTICS,
        percentiles=result.percentiles,
        median_min=result.median_min,
        median_max=result.median_max,
        histogram=[HistogramBin(lower=lo, upper=hi, count=n) for lo, hi, n in result.histogram],
        flag_counts=result.flag_counts,
        currency=COMPARABLE_CURRENCY,
        scope=dataset_scope(session, filters, freshness_window_days=window),
    )


@router.get("/salaries/compare", response_model=SalaryComparisonOut, tags=["salaries"])
def salary_compare(
    session: SessionDep,
    settings: SettingsDep,
    filters: FiltersDep,
    by: Dimension = Dimension.ROLE_FAMILY,
    limit: Annotated[int, Query(ge=1, le=MAX_BREAKDOWN_ROWS)] = 20,
) -> SalaryComparisonOut:
    """Quartiles of monthly salary midpoints per group. Groups with fewer than
    `min_records_for_statistics` usable salaries get null statistics."""
    if by in (Dimension.TITLE, Dimension.COMPANY):
        raise ApiError(
            422,
            "unsupported_dimension",
            "Perbandingan gaji per judul atau perusahaan tidak didukung "
            "karena sampelnya terlalu kecil.",
        )
    window = settings.freshness_window_days
    groups = salary.compare(session, by, filters, limit=limit, freshness_window_days=window)
    return SalaryComparisonOut(
        by=by.value,
        min_records_for_statistics=salary.MIN_RECORDS_FOR_STATISTICS,
        small_sample_threshold=salary.SMALL_SAMPLE_THRESHOLD,
        groups=[SalaryGroupOut(**vars(g)) for g in groups],
        scope=dataset_scope(session, filters, freshness_window_days=window),
    )


@router.get("/skills/source-tags", response_model=TagStatsOut, tags=["skills"])
def source_tag_stats(
    session: SessionDep,
    settings: SettingsDep,
    filters: FiltersDep,
    limit: Annotated[int, Query(ge=1, le=MAX_BREAKDOWN_ROWS)] = 20,
) -> TagStatsOut:
    """Tags visible on source listing cards. These are truncated previews, not a measure
    of skill demand; see `jobs_with_hidden_tags`."""
    window = settings.freshness_window_days
    result = tags.tag_stats(session, filters, limit=limit, freshness_window_days=window)
    return TagStatsOut(
        total_jobs=result.total_jobs,
        jobs_with_visible_tags=result.jobs_with_visible_tags,
        jobs_with_hidden_tags=result.jobs_with_hidden_tags,
        visible_tags=result.visible_tags,
        hidden_tags=result.hidden_tags,
        top_tags=[FilterOption(value=tag, label=tag, count=n) for tag, n in result.top_tags],
        role_families=[
            FilterOption(value=code, label=RoleFamily(code).label, count=n)
            for code, n in result.role_families
        ],
        scope=dataset_scope(session, filters, freshness_window_days=window),
    )


@router.get("/sources/coverage", response_model=list[SourceCoverage], tags=["sources"])
def source_coverage(session: SessionDep) -> list[SourceCoverage]:
    """Every registered source with its eligibility decision and contribution."""
    job_counts: dict[str, int] = dict(
        session.execute(select(Job.primary_source_id, func.count()).group_by(Job.primary_source_id))
        .tuples()
        .all()
    )
    last_success: dict[str, datetime | None] = dict(
        session.execute(
            select(IngestionRun.source_id, func.max(IngestionRun.finished_at))
            .where(IngestionRun.status == RunStatus.SUCCEEDED.value)
            .group_by(IngestionRun.source_id)
        )
        .tuples()
        .all()
    )
    sources = session.scalars(select(Source)).all()
    ordered = sorted(
        sources, key=lambda s: (-job_counts.get(s.id, 0), s.permission_status, s.name.casefold())
    )
    return [
        SourceCoverage.build(
            s, job_count=job_counts.get(s.id, 0), last_success=last_success.get(s.id)
        )
        for s in ordered
    ]
