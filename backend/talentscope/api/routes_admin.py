"""Administrator endpoints (bearer token). Read operational data and pause/resume
sources. Eligibility decisions and ingestion runs are CLI-only by design: exposing source
execution over HTTP would widen the attack surface for little benefit at this scale."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from talentscope.analytics.quality import quality_report
from talentscope.api.deps import AdminDep, SessionDep
from talentscope.api.errors import ApiError
from talentscope.api.schemas import Coded, Page
from talentscope.models import AuditEvent, IngestionRun, Source
from talentscope.sources import set_paused
from talentscope.vocab import PermissionStatus, RunErrorCategory, RunStatus

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

# Source IDs are short slugs (String(80)); anything else cannot exist and is a 422, which
# also keeps characters PostgreSQL rejects (NUL) away from the database.
_SOURCE_ID = {"max_length": 80, "pattern": "^[A-Za-z0-9._-]+$"}
SourceIdPath = Annotated[str, Path(**_SOURCE_ID)]


class AdminSource(BaseModel):
    id: str
    name: str
    canonical_domain: str | None
    category: str
    permission_status: Coded
    technical_method: str
    connector: str | None
    is_paused: bool
    decision_reason: str | None
    terms_url: str | None
    robots_url: str | None
    api_docs_url: str | None
    reviewed_at: datetime | None
    last_run_status: str | None
    last_run_at: datetime | None
    last_success_at: datetime | None


class RunOut(BaseModel):
    id: uuid.UUID
    source_id: str
    trigger: str
    mode: str
    status: Coded
    error_category: Coded | None
    message: str | None
    parser_version: str
    input_reference: str | None
    observed_at: datetime
    records_seen: int
    records_created: int
    records_updated: int
    records_unchanged: int
    records_rejected: int
    cross_source_matches: int
    details: dict[str, Any]
    started_at: datetime
    finished_at: datetime | None
    duration_seconds: float | None

    @classmethod
    def from_run(cls, run: IngestionRun) -> RunOut:
        return cls(
            id=run.id,
            source_id=run.source_id,
            trigger=run.trigger,
            mode=run.mode,
            status=Coded.of(RunStatus, run.status),
            error_category=Coded.of(RunErrorCategory, run.error_category)
            if run.error_category
            else None,
            message=run.message,
            parser_version=run.parser_version,
            input_reference=run.input_reference,
            observed_at=run.observed_at,
            records_seen=run.records_seen,
            records_created=run.records_created,
            records_updated=run.records_updated,
            records_unchanged=run.records_unchanged,
            records_rejected=run.records_rejected,
            cross_source_matches=run.cross_source_matches,
            details=run.details,
            started_at=run.started_at,
            finished_at=run.finished_at,
            duration_seconds=(run.finished_at - run.started_at).total_seconds()
            if run.finished_at
            else None,
        )


class PauseRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class AuditOut(BaseModel):
    id: int
    actor: str
    action: str
    entity_type: str
    entity_id: str
    reason: str | None
    details: dict[str, Any]
    created_at: datetime


class QualityOut(BaseModel):
    total_jobs: int
    total_source_records: int
    missing: dict[str, int]
    flags: dict[str, int]
    location_confidence: dict[str, int]
    salary_status: dict[str, int]
    same_source_fingerprint_groups: int
    jobs_in_fingerprint_groups: int
    normalization_versions: dict[str, int]


def _admin_sources(session: SessionDep, source_ids: list[str] | None = None) -> list[AdminSource]:
    latest = (
        select(IngestionRun.source_id, IngestionRun.status, IngestionRun.started_at)
        .distinct(IngestionRun.source_id)
        .order_by(IngestionRun.source_id, IngestionRun.started_at.desc())
    )
    last_run = {row.source_id: row for row in session.execute(latest)}
    last_success = dict(
        session.execute(
            select(IngestionRun.source_id, func.max(IngestionRun.finished_at))
            .where(IngestionRun.status == RunStatus.SUCCEEDED.value)
            .group_by(IngestionRun.source_id)
        )
        .tuples()
        .all()
    )
    query = select(Source).order_by(Source.id)
    if source_ids is not None:
        query = query.where(Source.id.in_(source_ids))
    return [
        AdminSource(
            id=s.id,
            name=s.name,
            canonical_domain=s.canonical_domain,
            category=s.category,
            permission_status=Coded.of(PermissionStatus, s.permission_status),
            technical_method=s.technical_method,
            connector=s.connector,
            is_paused=s.is_paused,
            decision_reason=s.decision_reason,
            terms_url=s.terms_url,
            robots_url=s.robots_url,
            api_docs_url=s.api_docs_url,
            reviewed_at=s.reviewed_at,
            last_run_status=last_run[s.id].status if s.id in last_run else None,
            last_run_at=last_run[s.id].started_at if s.id in last_run else None,
            last_success_at=last_success.get(s.id),
        )
        for s in session.scalars(query)
    ]


@router.get("/sources", response_model=list[AdminSource])
def list_sources(session: SessionDep, _: AdminDep) -> list[AdminSource]:
    return _admin_sources(session)


def _toggle(
    session: SessionDep, actor: str, source_id: str, paused: bool, reason: str
) -> AdminSource:
    source = session.get(Source, source_id)
    if source is None:
        raise ApiError(404, "source_not_found", "Sumber tidak ditemukan.")
    try:
        set_paused(session, source, paused, actor=actor, reason=reason)
    except PermissionError as exc:
        raise ApiError(409, "source_not_eligible", str(exc)) from exc
    session.commit()
    return _admin_sources(session, [source_id])[0]


@router.post("/sources/{source_id}/pause", response_model=AdminSource)
def pause_source(
    source_id: SourceIdPath, body: PauseRequest, session: SessionDep, actor: AdminDep
) -> AdminSource:
    return _toggle(session, actor, source_id, True, body.reason)


@router.post("/sources/{source_id}/resume", response_model=AdminSource)
def resume_source(
    source_id: SourceIdPath, body: PauseRequest, session: SessionDep, actor: AdminDep
) -> AdminSource:
    """Only APPROVED or APPROVED_WITH_CONDITIONS sources can be resumed (409 otherwise)."""
    return _toggle(session, actor, source_id, False, body.reason)


@router.get("/ingestion-runs", response_model=Page[RunOut])
def list_runs(
    session: SessionDep,
    _: AdminDep,
    source_id: Annotated[str | None, Query(**_SOURCE_ID)] = None,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> Page[RunOut]:
    query = select(IngestionRun)
    if source_id:
        query = query.where(IngestionRun.source_id == source_id)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    runs = session.scalars(
        query.order_by(IngestionRun.started_at.desc(), IngestionRun.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page[RunOut].build(
        [RunOut.from_run(r) for r in runs], page=page, page_size=page_size, total=total
    )


@router.get("/ingestion-runs/{run_id}", response_model=RunOut)
def get_run(run_id: uuid.UUID, session: SessionDep, _: AdminDep) -> RunOut:
    run = session.get(IngestionRun, run_id)
    if run is None:
        raise ApiError(404, "run_not_found", "Riwayat eksekusi tidak ditemukan.")
    return RunOut.from_run(run)


@router.get("/data-quality", response_model=QualityOut)
def data_quality(session: SessionDep, _: AdminDep) -> QualityOut:
    return QualityOut(**vars(quality_report(session)))


@router.get("/audit-events", response_model=Page[AuditOut])
def audit_events(
    session: SessionDep,
    _: AdminDep,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> Page[AuditOut]:
    total = session.scalar(select(func.count()).select_from(AuditEvent)) or 0
    events = session.scalars(
        select(AuditEvent)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [AuditOut.model_validate(e, from_attributes=True) for e in events]
    return Page[AuditOut].build(items, page=page, page_size=page_size, total=total)
