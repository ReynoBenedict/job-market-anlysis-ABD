from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from talentscope.analytics.filters import JobFilters, apply_filters
from talentscope.analytics.market import publisher_site
from talentscope.api.schemas import DatasetScope, SourceRef
from talentscope.models import Job, Source


def dataset_scope(
    session: Session, filters: JobFilters, *, freshness_window_days: int
) -> DatasetScope:
    """Period, sources, and coverage caveats for the filtered set of jobs."""
    filtered = apply_filters(
        select(Job), filters, freshness_window_days=freshness_window_days
    ).subquery()
    observed_from, observed_to, published_from, published_to, publisher_sites = session.execute(
        select(
            func.min(filtered.c.last_seen_at),
            func.max(filtered.c.last_seen_at),
            func.min(filtered.c.published_at),
            func.max(filtered.c.published_at),
            func.count(func.distinct(publisher_site(filtered.c.source_url))),
        )
    ).one()
    sources = session.scalars(
        select(Source)
        .where(Source.id.in_(select(filtered.c.primary_source_id).distinct()))
        .order_by(Source.name)
    ).all()
    cutoff = datetime.now(timezone.utc) - timedelta(days=freshness_window_days)
    return DatasetScope(
        observed_from=observed_from,
        observed_to=observed_to,
        published_from=published_from,
        published_to=published_to,
        is_historical=observed_to is None or observed_to < cutoff,
        freshness_window_days=freshness_window_days,
        sources=[SourceRef.from_source(s) for s in sources],
        publisher_sites=publisher_sites,
        coverage_notes=[s.coverage_note for s in sources if s.coverage_note],
    )
