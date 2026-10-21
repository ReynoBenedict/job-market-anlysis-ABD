"""Data-quality summaries for the admin workspace (SRS FR-ADMIN-005)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from talentscope.models import Job, SourceRecord

_MISSING_CHECKS = {
    "company_name": Job.company_name.is_(None),
    "city": Job.city.is_(None),
    "province": Job.province.is_(None),
    "employment_type": Job.employment_type == "UNKNOWN",
    "experience": Job.experience_band == "UNKNOWN",
    "education": Job.education_level == "UNKNOWN",
    "salary": Job.salary_status != "DISCLOSED",
    "description": Job.description.is_(None),
    "source_url": Job.source_url.is_(None),
    "published_at": Job.published_at.is_(None),
}


@dataclass(frozen=True)
class QualityReport:
    total_jobs: int
    total_source_records: int
    missing: dict[str, int]
    flags: dict[str, int]
    location_confidence: dict[str, int]
    salary_status: dict[str, int]
    same_source_fingerprint_groups: int
    jobs_in_fingerprint_groups: int
    normalization_versions: dict[str, int]


def quality_report(session: Session) -> QualityReport:
    total = session.scalar(select(func.count()).select_from(Job)) or 0
    records = session.scalar(select(func.count()).select_from(SourceRecord)) or 0
    missing_row = session.execute(
        select(*[func.count().filter(condition) for condition in _MISSING_CHECKS.values()])
    ).one()
    flag = func.unnest(Job.quality_flags).label("flag")
    flags = (
        session.execute(select(flag, func.count()).group_by(flag).order_by(func.count().desc()))
        .tuples()
        .all()
    )

    def counts(column: object) -> dict[str, int]:
        return dict(session.execute(select(column, func.count()).group_by(column)).tuples().all())  # type: ignore[call-overload]

    groups = (
        select(Job.primary_source_id, Job.fingerprint, func.count().label("n"))
        .group_by(Job.primary_source_id, Job.fingerprint)
        .having(func.count() > 1)
        .subquery()
    )
    group_row = session.execute(select(func.count(), func.coalesce(func.sum(groups.c.n), 0))).one()
    return QualityReport(
        total_jobs=total,
        total_source_records=records,
        missing=dict(zip(_MISSING_CHECKS, missing_row, strict=True)),
        flags=dict(flags),
        location_confidence=counts(Job.location_confidence),
        salary_status=counts(Job.salary_status),
        same_source_fingerprint_groups=group_row[0],
        jobs_in_fingerprint_groups=int(group_row[1]),
        normalization_versions=counts(Job.normalization_version),
    )
