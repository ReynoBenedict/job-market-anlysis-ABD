"""Statistics on source card tags.

These are the few tags a job board shows on a listing card, cut off after one to three
("+5" more hidden). They are reported as "tags seen on cards", never as skill demand,
because the hidden tags and job descriptions are missing (SRS FR-SKL-001/009).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from talentscope.analytics.filters import JobFilters, apply_filters
from talentscope.models import Job


@dataclass(frozen=True)
class TagStats:
    total_jobs: int
    jobs_with_visible_tags: int
    jobs_with_hidden_tags: int
    visible_tags: int
    hidden_tags: int
    top_tags: list[tuple[str, int]]
    # Jobs per role family among tag-showing sources, ignoring any role-family filter, so a
    # page can offer only the families that have tagged listings.
    role_families: list[tuple[str, int]]


def tag_stats(
    session: Session, filters: JobFilters, *, limit: int, freshness_window_days: int
) -> TagStats:
    # Only sources that show tags at all form the denominator; counting listings from a
    # source without tags (e.g. archived pages) as "no tags visible" would be misleading.
    tagging_sources = (
        select(Job.primary_source_id)
        .where(or_(func.cardinality(Job.source_tags) > 0, Job.hidden_tag_count > 0))
        .distinct()
    )
    filtered = (
        apply_filters(select(Job), filters, freshness_window_days=freshness_window_days)
        .where(Job.primary_source_id.in_(tagging_sources))
        .subquery()
    )
    any_role = filters.model_copy(update={"role_family": []})
    by_role = (
        apply_filters(
            select(Job.role_family, func.count()),
            any_role,
            freshness_window_days=freshness_window_days,
        )
        .where(Job.primary_source_id.in_(tagging_sources))
        .group_by(Job.role_family)
        .order_by(func.count().desc(), Job.role_family)
    )
    tag_count = func.cardinality(filtered.c.source_tags)
    summary = session.execute(
        select(
            func.count(),
            func.count().filter(tag_count > 0),
            func.count().filter(filtered.c.hidden_tag_count > 0),
            func.coalesce(func.sum(tag_count), 0),
            func.coalesce(func.sum(filtered.c.hidden_tag_count), 0),
        )
    ).one()
    tag = func.unnest(filtered.c.source_tags).label("tag")
    top = (
        session.execute(
            select(tag, func.count()).group_by(tag).order_by(func.count().desc(), tag).limit(limit)
        )
        .tuples()
        .all()
    )
    return TagStats(
        total_jobs=summary[0],
        jobs_with_visible_tags=summary[1],
        jobs_with_hidden_tags=summary[2],
        visible_tags=int(summary[3]),
        hidden_tags=int(summary[4]),
        top_tags=list(top),
        role_families=list(session.execute(by_role).tuples().all()),
    )
