"""Source eligibility gate checked before every run (SRS FR-SRC-002, FR-ING-004)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from talentscope.models import Source
from talentscope.vocab import RUNNABLE_PERMISSION_STATUSES, PermissionStatus

# Approvals are not permanent (SRS §3.4); a stale review blocks network collection.
REVIEW_VALID_FOR = timedelta(days=365)


class PolicyRefusal(Exception):
    pass


def ensure_runnable(source: Source, *, mode: str, now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    status = PermissionStatus(source.permission_status)
    if status not in RUNNABLE_PERMISSION_STATUSES:
        raise PolicyRefusal(
            f"source {source.id!r} is {status.value}; only approved sources may run"
        )
    if source.is_paused:
        raise PolicyRefusal(f"source {source.id!r} is paused by an operator")
    if source.connector is None:
        raise PolicyRefusal(f"source {source.id!r} has no connector configured")
    if mode == "collect":
        if source.reviewed_at is None:
            raise PolicyRefusal(f"source {source.id!r} has no recorded policy review")
        if now - source.reviewed_at > REVIEW_VALID_FOR:
            raise PolicyRefusal(
                f"source {source.id!r} policy review from {source.reviewed_at:%Y-%m-%d} has expired"
            )


def can_resume(source: Source) -> bool:
    """Resuming is only an operational toggle; it never upgrades eligibility."""
    return PermissionStatus(source.permission_status) in RUNNABLE_PERMISSION_STATUSES
