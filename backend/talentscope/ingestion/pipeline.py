"""The shared ingestion pipeline: policy gate -> fetch -> normalize -> upsert -> report.

Idempotency: a source record is identified by (source_id, source_key). Running the same
input again updates ``last_seen_at`` and leaves the data unchanged; it never creates
duplicates. Records that a run does not return are not deleted; their freshness is
derived from ``last_seen_at`` instead (see docs/PIPELINE.md).

The exception is a connector whose input is a complete rebuilt snapshot
(``Connector.replaces_snapshot``, e.g. `lake publish`). Such a run is all or nothing: its
records are written in one transaction together with ``retire_unlisted_records``, and any
failure, rejected record, or record limit rolls the data back, so the app never shows a
half-applied snapshot mixed with the previous one as if it were complete. Other
connectors commit every ``COMMIT_EVERY`` records, and what they committed stays.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from talentscope.ingestion.connectors import build_connector
from talentscope.ingestion.connectors.base import Connector
from talentscope.ingestion.http import PoliteClient
from talentscope.ingestion.policy import PolicyRefusal, ensure_runnable
from talentscope.ingestion.records import ConnectorError, SourceJob
from talentscope.models import AuditEvent, IngestionRun, Job, Source, SourceRecord
from talentscope.normalization.job import (
    NORMALIZATION_VERSION,
    InvalidSourceJob,
    NormalizedJob,
    normalize_source_job,
)
from talentscope.vocab import RunErrorCategory, RunStatus

logger = logging.getLogger(__name__)

COMMIT_EVERY = 250
MAX_REJECTION_SAMPLES = 20

Outcome = Literal["created", "updated", "unchanged"]


@dataclass
class _Counts:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    matched: int = 0

    @property
    def accepted(self) -> int:
        return self.created + self.updated + self.unchanged


def run_source(
    session: Session,
    source: Source,
    *,
    client: PoliteClient | None,
    trigger: str = "cli",
    max_records: int | None = None,
) -> IngestionRun:
    """Entry point for operators: refuse ineligible sources before any connector is built,
    so blocked sources leave an auditable REFUSED run instead of a stack trace."""
    mode = "import" if source.technical_method == "manual_import" else "collect"
    try:
        ensure_runnable(source, mode=mode)
    except PolicyRefusal as refusal:
        run = IngestionRun(
            source_id=source.id,
            trigger=trigger,
            mode=mode,
            status=RunStatus.RUNNING.value,
            parser_version="-",
            observed_at=datetime.now(timezone.utc),
            details={},
        )
        session.add(run)
        _finish(run, RunStatus.REFUSED, RunErrorCategory.POLICY_BLOCKED, str(refusal))
        session.commit()
        logger.warning(
            "ingestion refused by source policy",
            extra={"source_id": source.id, "reason": str(refusal)},
        )
        return run
    connector = build_connector(source, client=client)
    return run_connector(session, source, connector, trigger=trigger, max_records=max_records)


def run_connector(
    session: Session,
    source: Source,
    connector: Connector,
    *,
    trigger: str = "cli",
    max_records: int | None = None,
) -> IngestionRun:
    """Execute one run and return its persisted ``IngestionRun``.

    Connector failures end the run with a categorized status. Unexpected exceptions
    (bugs) are recorded as INTERNAL and then re-raised, never swallowed.
    """
    run = IngestionRun(
        source_id=source.id,
        trigger=trigger,
        mode=connector.mode,
        status=RunStatus.RUNNING.value,
        parser_version=connector.parser_version,
        observed_at=connector.observed_at(),
        details={},
    )
    session.add(run)
    session.flush()
    log = {"run_id": str(run.id), "source_id": source.id}

    try:
        ensure_runnable(source, mode=connector.mode)
    except PolicyRefusal as refusal:
        _finish(run, RunStatus.REFUSED, RunErrorCategory.POLICY_BLOCKED, str(refusal))
        session.commit()
        logger.warning("ingestion refused by source policy", extra={**log, "reason": str(refusal)})
        return run

    run.input_reference = connector.describe_input()
    session.commit()
    logger.info("ingestion started", extra=log)

    counts = _Counts()
    rejections: list[dict[str, str]] = []
    try:
        for source_job in connector.fetch():
            if max_records is not None and run.records_seen >= max_records:
                run.details = {**run.details, "stopped_at_record_limit": max_records}
                break
            run.records_seen += 1
            try:
                normalized = normalize_source_job(
                    source_job,
                    observed_at=run.observed_at,
                    salary_convention=connector.salary_convention,
                )
            except InvalidSourceJob as exc:
                run.records_rejected += 1
                if len(rejections) < MAX_REJECTION_SAMPLES:
                    rejections.append({"source_key": source_job.source_key, "reason": str(exc)})
                continue
            outcome, matched = _upsert(session, source, run, source_job, normalized)
            setattr(counts, outcome, getattr(counts, outcome) + 1)
            counts.matched += matched
            if run.records_seen % COMMIT_EVERY == 0 and not connector.replaces_snapshot:
                _store_counts(run, counts)
                session.commit()
    except ConnectorError as exc:
        if connector.replaces_snapshot:
            return _abandon_snapshot(
                session, run, counts, exc.category, f"{exc}; nothing was published", rejections
            )
        _store_counts(run, counts)
        status = RunStatus.PARTIAL if counts.accepted else RunStatus.FAILED
        _finish(run, status, exc.category, str(exc), rejections)
        session.commit()
        logger.error(
            "ingestion stopped by connector error", extra={**log, "category": exc.category.value}
        )
        return run
    except Exception:
        session.rollback()
        failed = session.get(IngestionRun, run.id)
        if failed is not None:
            _finish(
                failed,
                RunStatus.FAILED,
                RunErrorCategory.INTERNAL,
                "unexpected error; see server logs",
            )
            session.commit()
        logger.exception("ingestion crashed", extra=log)
        raise

    if connector.replaces_snapshot:
        limited = "stopped_at_record_limit" in run.details
        if run.records_rejected or limited:
            reason = "a record limit was set" if limited else "some records were rejected"
            return _abandon_snapshot(
                session,
                run,
                counts,
                RunErrorCategory.INVALID_RECORDS if run.records_rejected else None,
                f"incomplete snapshot ({reason}); nothing was published",
                rejections,
            )
        records, jobs = retire_unlisted_records(
            session, source, connector.current_keys(), actor=f"run:{run.id}"
        )
        run.details = {**run.details, "retired_records": records, "retired_jobs": jobs}

    _store_counts(run, counts)
    if run.records_rejected == 0:
        _finish(run, RunStatus.SUCCEEDED, None, None, rejections)
    elif counts.accepted == 0:
        _finish(
            run,
            RunStatus.FAILED,
            RunErrorCategory.INVALID_RECORDS,
            "every record was rejected",
            rejections,
        )
    else:
        _finish(
            run,
            RunStatus.PARTIAL,
            RunErrorCategory.INVALID_RECORDS,
            "some records were rejected",
            rejections,
        )
    if run.records_seen == 0:
        run.details = {**run.details, "empty_result": True}
    session.commit()
    logger.info(
        "ingestion finished",
        extra={
            **log,
            "status": run.status,
            "seen": run.records_seen,
            "rejected": run.records_rejected,
        },
    )
    return run


def _abandon_snapshot(
    session: Session,
    run: IngestionRun,
    counts: _Counts,
    category: RunErrorCategory | None,
    message: str,
    rejections: list[dict[str, str]],
) -> IngestionRun:
    """Roll back an incomplete snapshot run's records and keep only the failed run row,
    with the counts it reached, so operators can see what happened."""
    seen, rejected, details = run.records_seen, run.records_rejected, dict(run.details)
    session.rollback()
    failed = session.get(IngestionRun, run.id)
    assert failed is not None  # committed before fetching started
    failed.records_seen, failed.records_rejected = seen, rejected
    failed.details = {**details, "rolled_back": True}
    _store_counts(failed, counts)
    _finish(failed, RunStatus.FAILED, category, message, rejections)
    session.commit()
    logger.error(
        "snapshot run rolled back",
        extra={"run_id": str(failed.id), "source_id": failed.source_id, "reason": message},
    )
    return failed


def _store_counts(run: IngestionRun, counts: _Counts) -> None:
    run.records_created = counts.created
    run.records_updated = counts.updated
    run.records_unchanged = counts.unchanged
    run.cross_source_matches = counts.matched


def _finish(
    run: IngestionRun,
    status: RunStatus,
    category: RunErrorCategory | None,
    message: str | None,
    rejections: list[dict[str, str]] | None = None,
) -> None:
    run.status = status.value
    run.error_category = category.value if category else None
    run.message = message
    run.finished_at = datetime.now(timezone.utc)
    if rejections:
        run.details = {**run.details, "rejection_samples": rejections}


def _upsert(
    session: Session,
    source: Source,
    run: IngestionRun,
    source_job: SourceJob,
    normalized: NormalizedJob,
) -> tuple[Outcome, bool]:
    observed_at = source_job.last_observed_at or run.observed_at
    first_observed_at = source_job.first_observed_at or observed_at
    record = session.scalar(
        select(SourceRecord).where(
            SourceRecord.source_id == source.id, SourceRecord.source_key == source_job.source_key
        )
    )
    if record is not None:
        job = record.job
        record.last_seen_at = max(record.last_seen_at, observed_at)
        record.first_seen_at = min(record.first_seen_at, first_observed_at)
        record.last_run_id = run.id
        job.last_seen_at = max(job.last_seen_at, observed_at)
        job.first_seen_at = min(job.first_seen_at, first_observed_at)
        content_changed = record.content_hash != normalized.content_hash
        rules_changed = job.normalization_version != NORMALIZATION_VERSION
        if not (content_changed or rules_changed):
            return "unchanged", False
        record.content_hash = normalized.content_hash
        record.raw_fields = dict(source_job.raw_fields)
        record.parser_version = run.parser_version
        # Only the job's primary source may rewrite its canonical fields.
        if job.primary_source_id == source.id:
            for column, value in normalized.values.items():
                setattr(job, column, value)
            job.fingerprint = normalized.fingerprint
        return "updated", False

    match = _find_cross_source_match(session, source, normalized)
    if match is not None:
        job, match_rule = match, "cross_source_fingerprint"
        job.last_seen_at = max(job.last_seen_at, observed_at)
    else:
        match_rule = "new_job"
        job = Job(
            primary_source_id=source.id,
            fingerprint=normalized.fingerprint,
            first_seen_at=first_observed_at,
            last_seen_at=observed_at,
            **normalized.values,
        )
        session.add(job)
    session.add(
        SourceRecord(
            source_id=source.id,
            source_key=source_job.source_key,
            source_key_kind=source_job.source_key_kind,
            source_url=normalized.values["source_url"],
            job=job,
            match_rule=match_rule,
            content_hash=normalized.content_hash,
            raw_fields=dict(source_job.raw_fields),
            parser_version=run.parser_version,
            first_seen_at=first_observed_at,
            last_seen_at=observed_at,
            first_run_id=run.id,
            last_run_id=run.id,
        )
    )
    session.flush()
    return "created", match_rule != "new_job"


def _find_cross_source_match(
    session: Session, source: Source, normalized: NormalizedJob
) -> Job | None:
    """Link to a job from another source only when exactly one candidate shares the
    fingerprint (normalized title, company, and city). Ambiguous cases stay separate:
    a missed merge is safer than merging two distinct vacancies (SRS FR-DUP-004).
    Records from the same source are never merged, since one employer can post the
    same title for different openings."""
    candidates = session.scalars(
        select(Job)
        .where(Job.fingerprint == normalized.fingerprint, Job.primary_source_id != source.id)
        .limit(2)
    ).all()
    return candidates[0] if len(candidates) == 1 else None


def retire_unlisted_records(
    session: Session, source: Source, current_keys: set[str], *, actor: str
) -> tuple[int, int]:
    """Remove a source's records that its latest complete input no longer contains.

    Only for sources whose input is a complete, rebuilt snapshot, such as the lake's
    canonical vacancies: a vacancy that a rebuild merged into another one must not stay
    in the app as a duplicate. Jobs left without any source record are deleted; jobs
    still backed by another source's record are kept. Returns (records, jobs) removed.
    """
    stale = [
        record
        for record in session.scalars(
            select(SourceRecord).where(SourceRecord.source_id == source.id)
        )
        if record.source_key not in current_keys
    ]
    job_ids = {record.job_id for record in stale}
    for record in stale:
        session.delete(record)
    session.flush()
    still_backed = set(
        session.scalars(select(SourceRecord.job_id).where(SourceRecord.job_id.in_(job_ids)))
    )
    orphaned = list(session.scalars(select(Job).where(Job.id.in_(job_ids - still_backed))))
    for job in orphaned:
        session.delete(job)
    if stale:
        session.add(
            AuditEvent(
                actor=actor,
                action="source.records_retired",
                entity_type="source",
                entity_id=source.id,
                reason="no longer present in the source's latest complete input",
                details={"records": len(stale), "jobs": len(orphaned)},
            )
        )
    session.flush()
    return len(stale), len(orphaned)
