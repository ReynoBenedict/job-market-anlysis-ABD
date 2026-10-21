from datetime import datetime, timedelta, timezone

import pytest

from talentscope.ingestion.policy import PolicyRefusal, can_resume, ensure_runnable
from talentscope.models import Source
from talentscope.vocab import PermissionStatus

NOW = datetime(2026, 10, 17, tzinfo=timezone.utc)


def _source(status: PermissionStatus, **overrides: object) -> Source:
    fields: dict[str, object] = {
        "id": "example",
        "name": "Example",
        "category": "ats_api",
        "technical_method": "api",
        "permission_status": status.value,
        "connector": "lever",
        "is_paused": False,
        "reviewed_at": NOW - timedelta(days=10),
    }
    fields.update(overrides)
    return Source(**fields)


@pytest.mark.parametrize(
    "status",
    [
        PermissionStatus.BLOCKED,
        PermissionStatus.NEEDS_REVIEW,
        PermissionStatus.REQUIRES_WRITTEN_PERMISSION,
        PermissionStatus.DISCOVERED,
        PermissionStatus.PAUSED,
        PermissionStatus.RETIRED,
    ],
)
def test_unapproved_sources_never_run(status: PermissionStatus) -> None:
    with pytest.raises(PolicyRefusal):
        ensure_runnable(_source(status), mode="collect", now=NOW)
    assert not can_resume(_source(status))


@pytest.mark.parametrize(
    "status", [PermissionStatus.APPROVED, PermissionStatus.APPROVED_WITH_CONDITIONS]
)
def test_approved_sources_run(status: PermissionStatus) -> None:
    ensure_runnable(_source(status), mode="collect", now=NOW)
    assert can_resume(_source(status))


def test_paused_source_does_not_run() -> None:
    with pytest.raises(PolicyRefusal, match="paused"):
        ensure_runnable(_source(PermissionStatus.APPROVED, is_paused=True), mode="collect", now=NOW)


def test_expired_review_blocks_network_collection_only() -> None:
    stale = _source(PermissionStatus.APPROVED, reviewed_at=NOW - timedelta(days=400))
    with pytest.raises(PolicyRefusal, match="expired"):
        ensure_runnable(stale, mode="collect", now=NOW)
    ensure_runnable(stale, mode="import", now=NOW)


def test_source_without_connector_cannot_run() -> None:
    with pytest.raises(PolicyRefusal, match="connector"):
        ensure_runnable(_source(PermissionStatus.APPROVED, connector=None), mode="import", now=NOW)
