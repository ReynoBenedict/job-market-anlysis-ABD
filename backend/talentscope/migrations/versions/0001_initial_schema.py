"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-17 12:09:39.704351
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Trigram matching backs the job search (see docs/adr/0004-data-model-and-search.md).
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_events_created_at"), "audit_events", ["created_at"], unique=False
    )
    op.create_table(
        "sources",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("canonical_domain", sa.String(length=200), nullable=True),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("permission_status", sa.String(length=40), nullable=False),
        sa.Column("technical_method", sa.String(length=40), nullable=False),
        sa.Column("connector", sa.String(length=80), nullable=True),
        sa.Column("connector_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_paused", sa.Boolean(), nullable=False),
        sa.Column("terms_url", sa.Text(), nullable=True),
        sa.Column("robots_url", sa.Text(), nullable=True),
        sa.Column("api_docs_url", sa.Text(), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("attribution_text", sa.Text(), nullable=True),
        sa.Column("retention_constraints", sa.Text(), nullable=True),
        sa.Column("coverage_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "permission_status IN ('DISCOVERED', 'NEEDS_REVIEW', 'APPROVED', 'APPROVED_WITH_CONDITIONS', 'REQUIRES_WRITTEN_PERMISSION', 'BLOCKED', 'PAUSED', 'RETIRED')",
            name="valid_permission",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.String(length=80), nullable=False),
        sa.Column("trigger", sa.String(length=20), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_category", sa.String(length=40), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("parser_version", sa.String(length=40), nullable=False),
        sa.Column("input_reference", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("records_seen", sa.Integer(), nullable=False),
        sa.Column("records_created", sa.Integer(), nullable=False),
        sa.Column("records_updated", sa.Integer(), nullable=False),
        sa.Column("records_unchanged", sa.Integer(), nullable=False),
        sa.Column("records_rejected", sa.Integer(), nullable=False),
        sa.Column("cross_source_matches", sa.Integer(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'SUCCEEDED', 'PARTIAL', 'FAILED', 'REFUSED')",
            name="valid_status",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ingestion_runs_source_started",
        "ingestion_runs",
        ["source_id", "started_at"],
        unique=False,
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("primary_source_id", sa.String(length=80), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("role_family", sa.String(length=40), nullable=False),
        sa.Column("company_name", sa.Text(), nullable=True),
        sa.Column("location_text", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("province", sa.String(length=60), nullable=True),
        sa.Column("location_confidence", sa.String(length=30), nullable=False),
        sa.Column("employment_type_text", sa.Text(), nullable=True),
        sa.Column("employment_type", sa.String(length=30), nullable=False),
        sa.Column("work_arrangement", sa.String(length=20), nullable=False),
        sa.Column("work_arrangement_evidence", sa.Text(), nullable=True),
        sa.Column("experience_text", sa.Text(), nullable=True),
        sa.Column("experience_min_years", sa.Integer(), nullable=True),
        sa.Column("experience_max_years", sa.Integer(), nullable=True),
        sa.Column("experience_band", sa.String(length=20), nullable=False),
        sa.Column("education_text", sa.Text(), nullable=True),
        sa.Column("education_level", sa.String(length=20), nullable=False),
        sa.Column("salary_text", sa.Text(), nullable=True),
        sa.Column("salary_status", sa.String(length=20), nullable=False),
        sa.Column("salary_min", sa.BigInteger(), nullable=True),
        sa.Column("salary_max", sa.BigInteger(), nullable=True),
        sa.Column("salary_currency", sa.String(length=3), nullable=True),
        sa.Column("salary_period", sa.String(length=10), nullable=False),
        sa.Column("salary_period_assumed", sa.Boolean(), nullable=False),
        sa.Column("salary_monthly_min", sa.BigInteger(), nullable=True),
        sa.Column("salary_monthly_max", sa.BigInteger(), nullable=True),
        sa.Column("source_tags", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("hidden_tag_count", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("posted_text", sa.Text(), nullable=True),
        sa.Column("posted_age_days", sa.Integer(), nullable=True),
        sa.Column("is_urgent", sa.Boolean(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("quality_flags", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("normalization_version", sa.String(length=40), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "salary_status = 'DISCLOSED' OR (salary_min IS NULL AND salary_max IS NULL)",
            name="salary_amounts_only_when_disclosed",
        ),
        sa.CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="salary_bounds_ordered",
        ),
        sa.ForeignKeyConstraint(
            ["primary_source_id"],
            ["sources.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_employment_type", "jobs", ["employment_type"], unique=False)
    op.create_index("ix_jobs_fingerprint", "jobs", ["fingerprint"], unique=False)
    op.create_index("ix_jobs_last_seen", "jobs", ["last_seen_at"], unique=False)
    op.create_index("ix_jobs_province_city", "jobs", ["province", "city"], unique=False)
    op.create_index("ix_jobs_role_family", "jobs", ["role_family"], unique=False)
    op.create_index(
        "ix_jobs_search_text_trgm",
        "jobs",
        ["search_text"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"search_text": "gin_trgm_ops"},
    )
    op.create_table(
        "source_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.String(length=80), nullable=False),
        sa.Column("source_key", sa.String(length=200), nullable=False),
        sa.Column("source_key_kind", sa.String(length=30), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("match_rule", sa.String(length=40), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("parser_version", sa.String(length=40), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_run_id", sa.UUID(), nullable=False),
        sa.Column("last_run_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["first_run_id"],
            ["ingestion_runs.id"],
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["last_run_id"],
            ["ingestion_runs.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "source_key", name="uq_source_records_key"),
    )
    op.create_index(op.f("ix_source_records_job_id"), "source_records", ["job_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_source_records_job_id"), table_name="source_records")
    op.drop_table("source_records")
    op.drop_index(
        "ix_jobs_search_text_trgm",
        table_name="jobs",
        postgresql_using="gin",
        postgresql_ops={"search_text": "gin_trgm_ops"},
    )
    op.drop_index("ix_jobs_role_family", table_name="jobs")
    op.drop_index("ix_jobs_province_city", table_name="jobs")
    op.drop_index("ix_jobs_last_seen", table_name="jobs")
    op.drop_index("ix_jobs_fingerprint", table_name="jobs")
    op.drop_index("ix_jobs_employment_type", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_ingestion_runs_source_started", table_name="ingestion_runs")
    op.drop_table("ingestion_runs")
    op.drop_table("sources")
    op.drop_index(op.f("ix_audit_events_created_at"), table_name="audit_events")
    op.drop_table("audit_events")
