"""Database schema.

Entities and why each exists (see docs/adr/0004-data-model-and-search.md):

* ``Source``          - registry of job-data origins with their eligibility decision.
* ``IngestionRun``    - one execution of a connector or import, with outcome and counts.
* ``SourceRecord``    - a job as one source presented it, with provenance.
* ``Job``             - the canonical, normalized vacancy that search and analytics use.
                        Several source records can point at one job (cross-source match).
* ``AuditEvent``      - append-only log of policy-affecting changes.

Companies, skills, and users are deliberately not separate tables yet: company names
are not reliably resolvable to entities, skill data is too sparse to normalize, and the
product has no accounts (saved jobs live in the browser).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from talentscope.db import Base
from talentscope.vocab import PermissionStatus, RunStatus


def _codes(enum: type[Any]) -> str:
    return ", ".join(f"'{member.value}'" for member in enum)


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint(
            f"permission_status IN ({_codes(PermissionStatus)})", name="valid_permission"
        ),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    canonical_domain: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(40))
    permission_status: Mapped[str] = mapped_column(String(40))
    technical_method: Mapped[str] = mapped_column(String(40))
    # The adapter that can collect from this source, if one exists, and its settings.
    connector: Mapped[str | None] = mapped_column(String(80))
    connector_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Operational switch, independent of permission: an approved source can be paused.
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    terms_url: Mapped[str | None] = mapped_column(Text)
    robots_url: Mapped[str | None] = mapped_column(Text)
    api_docs_url: Mapped[str | None] = mapped_column(Text)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    attribution_text: Mapped[str | None] = mapped_column(Text)
    retention_constraints: Mapped[str | None] = mapped_column(Text)
    coverage_note: Mapped[str | None] = mapped_column(Text)
    # What the public site says about reuse rights, independent of the internal eligibility
    # gate in permission_status: a short badge and a one-sentence condition (Indonesian).
    public_label: Mapped[str | None] = mapped_column(Text)
    public_condition: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    runs: Mapped[list[IngestionRun]] = relationship(back_populates="source")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        CheckConstraint(f"status IN ({_codes(RunStatus)})", name="valid_status"),
        Index("ix_ingestion_runs_source_started", "source_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    trigger: Mapped[str] = mapped_column(String(20))  # "cli" or "admin"
    mode: Mapped[str] = mapped_column(String(20))  # "import" (file) or "collect" (network)
    status: Mapped[str] = mapped_column(String(20))
    error_category: Mapped[str | None] = mapped_column(String(40))
    message: Mapped[str | None] = mapped_column(Text)
    parser_version: Mapped[str] = mapped_column(String(40))
    # File name and SHA-256 for imports; endpoint description for network connectors.
    input_reference: Mapped[str | None] = mapped_column(Text)
    # Moment the data describes. For a historical import this predates `started_at`.
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    records_seen: Mapped[int] = mapped_column(Integer, default=0)
    records_created: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_unchanged: Mapped[int] = mapped_column(Integer, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, default=0)
    cross_source_matches: Mapped[int] = mapped_column(Integer, default=0)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source: Mapped[Source] = relationship(back_populates="runs")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="salary_bounds_ordered",
        ),
        CheckConstraint(
            "salary_status = 'DISCLOSED' OR (salary_min IS NULL AND salary_max IS NULL)",
            name="salary_amounts_only_when_disclosed",
        ),
        Index("ix_jobs_province_city", "province", "city"),
        Index("ix_jobs_role_family", "role_family"),
        Index("ix_jobs_employment_type", "employment_type"),
        Index("ix_jobs_fingerprint", "fingerprint"),
        Index("ix_jobs_last_seen", "last_seen_at"),
        Index(
            "ix_jobs_search_text_trgm",
            "search_text",
            postgresql_using="gin",
            postgresql_ops={"search_text": "gin_trgm_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    primary_source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    # Normalized title + company + city, used to propose cross-source matches.
    fingerprint: Mapped[str] = mapped_column(String(64))

    title: Mapped[str] = mapped_column(Text)
    role_family: Mapped[str] = mapped_column(String(40))
    company_name: Mapped[str | None] = mapped_column(Text)

    location_text: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    province: Mapped[str | None] = mapped_column(String(60))
    location_confidence: Mapped[str] = mapped_column(String(30))

    employment_type_text: Mapped[str | None] = mapped_column(Text)
    employment_type: Mapped[str] = mapped_column(String(30))
    work_arrangement: Mapped[str] = mapped_column(String(20))
    work_arrangement_evidence: Mapped[str | None] = mapped_column(Text)
    experience_text: Mapped[str | None] = mapped_column(Text)
    experience_min_years: Mapped[int | None] = mapped_column(Integer)
    experience_max_years: Mapped[int | None] = mapped_column(Integer)
    experience_band: Mapped[str] = mapped_column(String(20))
    education_text: Mapped[str | None] = mapped_column(Text)
    education_level: Mapped[str] = mapped_column(String(20))

    salary_text: Mapped[str | None] = mapped_column(Text)
    salary_status: Mapped[str] = mapped_column(String(20))
    salary_min: Mapped[int | None] = mapped_column(BigInteger)
    salary_max: Mapped[int | None] = mapped_column(BigInteger)
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    salary_period: Mapped[str] = mapped_column(String(10))
    salary_period_assumed: Mapped[bool] = mapped_column(Boolean, default=False)
    salary_monthly_min: Mapped[int | None] = mapped_column(BigInteger)
    salary_monthly_max: Mapped[int | None] = mapped_column(BigInteger)

    # Card tags from the source. Truncated previews, not full requirements.
    source_tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    hidden_tag_count: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text)

    posted_text: Mapped[str | None] = mapped_column(Text)
    posted_age_days: Mapped[int | None] = mapped_column(Integer)
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    source_url: Mapped[str | None] = mapped_column(Text)
    quality_flags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    normalization_version: Mapped[str] = mapped_column(String(40))

    # Lower-cased title, company, location, and tags; matched with pg_trgm. Built during
    # normalization because Postgres generated columns cannot use array_to_string.
    search_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    source_records: Mapped[list[SourceRecord]] = relationship(back_populates="job")
    primary_source: Mapped[Source] = relationship()


class SourceRecord(Base):
    __tablename__ = "source_records"
    __table_args__ = (UniqueConstraint("source_id", "source_key", name="uq_source_records_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    source_key: Mapped[str] = mapped_column(String(200))
    # "source_id": the source's own identifier; "url": its canonical URL;
    # "content_fingerprint": derived from content because the source offered neither.
    source_key_kind: Mapped[str] = mapped_column(String(30))
    source_url: Mapped[str | None] = mapped_column(Text)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    match_rule: Mapped[str] = mapped_column(String(40))  # how the record was linked to its job
    content_hash: Mapped[str] = mapped_column(String(64))
    raw_fields: Mapped[dict[str, Any]] = mapped_column(JSONB)
    parser_version: Mapped[str] = mapped_column(String(40))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    first_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingestion_runs.id"))
    last_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingestion_runs.id"))

    job: Mapped[Job] = relationship(back_populates="source_records")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(60))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
