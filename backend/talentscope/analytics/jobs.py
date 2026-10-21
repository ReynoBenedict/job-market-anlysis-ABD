from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy import Select, case, func, nulls_last, select
from sqlalchemy.orm import Session, selectinload

from talentscope.analytics.filters import JobFilters, apply_filters
from talentscope.analytics.salary_rule import comparable_salary
from talentscope.models import Job


class JobSort(str, Enum):
    RELEVANCE = "relevance"
    NEWEST = "newest"
    SALARY_DESC = "salary_desc"
    TITLE = "title"
    COMPANY = "company"


def _ordered(stmt: Select[tuple[Job]], sort: JobSort, filters: JobFilters) -> Select[tuple[Job]]:
    # Job.id is always the final key so pagination is stable across requests.
    if sort is JobSort.RELEVANCE and filters.q:
        return stmt.order_by(
            func.word_similarity(filters.q.casefold(), func.lower(Job.title)).desc(), Job.id
        )
    if sort is JobSort.SALARY_DESC:
        # Salaries that are not comparable (analytics.salary_rule) sort with unknown ones.
        comparable_max = case((comparable_salary(Job), Job.salary_monthly_max), else_=None)
        return stmt.order_by(nulls_last(comparable_max.desc()), Job.id)
    if sort is JobSort.TITLE:
        return stmt.order_by(func.lower(Job.title), Job.id)
    if sort is JobSort.COMPANY:
        return stmt.order_by(nulls_last(func.lower(Job.company_name)), Job.id)
    # Newest: latest posting date. Archived pages state it; the snapshot only states an age
    # relative to its observation date, from which the posting date is derived.
    posted_on = func.coalesce(
        Job.published_at,
        Job.last_seen_at - func.make_interval(0, 0, 0, func.coalesce(Job.posted_age_days, 0)),
    )
    # Listings the source marks as expired go last: they are rarely what a job seeker wants.
    expired_last = case((Job.expires_at < func.now(), 1), else_=0)
    return stmt.order_by(expired_last, posted_on.desc(), Job.id)


def search_jobs(
    session: Session,
    filters: JobFilters,
    *,
    sort: JobSort,
    page: int,
    page_size: int,
    freshness_window_days: int,
) -> tuple[list[Job], int]:
    base = apply_filters(select(Job), filters, freshness_window_days=freshness_window_days)
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = session.scalars(
        _ordered(base, sort, filters)
        .options(selectinload(Job.primary_source))
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total


def get_job(session: Session, job_id: uuid.UUID) -> Job | None:
    return session.scalar(
        select(Job)
        .where(Job.id == job_id)
        .options(selectinload(Job.primary_source), selectinload(Job.source_records))
    )
