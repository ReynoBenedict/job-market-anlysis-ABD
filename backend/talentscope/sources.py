"""Source registry maintenance: syncing reviewed decisions and audited status changes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from talentscope.ingestion.policy import can_resume
from talentscope.models import AuditEvent, Source
from talentscope.vocab import PermissionStatus

LEGACY_SNAPSHOT_SOURCE_ID = "glints-snapshot-2026-06"

# The historical dataset is not in the research matrix: it is not a live source but an
# existing file. The project owner instructed its use on 2026-10-17; the conditions
# below are shown to users and are why it is "approved with conditions" only.
LEGACY_SNAPSHOT_SOURCE: dict[str, Any] = {
    "id": LEGACY_SNAPSHOT_SOURCE_ID,
    "name": "Glints Indonesia — snapshot Juni 2026",
    "canonical_domain": "glints.com",
    "category": "dataset",
    "permission_status": PermissionStatus.APPROVED_WITH_CONDITIONS.value,
    "technical_method": "manual_import",
    "connector": "legacy_glints_csv",
    "connector_config": {
        "path": "data/raw/glints_jobs.csv",
        # Upper bound: commit time of the raw CSV (2026-06-13 02:57 WIB).
        "observed_at": "2026-06-12T19:57:02+00:00",
    },
    "terms_url": "https://glints.com/id/about/terms",
    "robots_url": None,
    "api_docs_url": None,
    "decision_reason": (
        "Existing academic snapshot (1 file, collected on or before 2026-06-13) imported "
        "read-only as historical data at the project owner's instruction of 2026-10-17. No new "
        "collection from Glints is performed: its terms prohibit automated extraction without "
        "written consent. Conditions: label as historical, attribute Glints, do not refresh, and "
        "review redistribution rights before any public deployment. Collected by the academic "
        "project's Selenium scraper of glints.com "
        "(legacy/academic_pipeline/scrapers/glints_scraper.py); no permission from Glints is on "
        "record."
    ),
    "attribution_text": (
        "Data lowongan berasal dari Glints Indonesia (glints.com), dikumpulkan pada atau sebelum "
        "13 Juni 2026 untuk proyek akademik. TalentScope tidak berafiliasi dengan Glints. "
        "TalentScope tidak memiliki izin khusus dari Glints."
    ),
    "retention_constraints": "Historical snapshot only; no refresh. Remove on request from Glints.",
    "coverage_note": (
        "Hasil pencarian Glints untuk 44 kata kunci (kebanyakan bidang teknologi, data, dan "
        "bisnis), dikumpulkan sekali pada Juni 2026."
    ),
    "public_label": "Data historis — hak tayang ulang belum dipastikan",
    "public_condition": (
        "Snapshot ini dikumpulkan sekali untuk proyek akademik pada Juni 2026 dan dipakai atas "
        "keputusan pemilik proyek, bukan atas izin Glints; sebelum situs ini dibuka untuk umum, "
        "hak menampilkan ulang lowongannya harus dikonfirmasi ke Glints atau tampilannya "
        "dibatasi pada angka ringkasan."
    ),
    "reviewed_at": datetime(2026, 10, 18, tzinfo=timezone.utc),
}


COMMON_CRAWL_SOURCE_ID = "commoncrawl-jobposting"

# Reviewed 2026-10-17 against https://commoncrawl.org/terms-of-use: the archive may be used
# under a limited licence, but crawled content stays subject to each site owner's terms.
# Hence the portal exclusions in talentscope/lake/domains.py, the per-site default-deny
# review in talentscope/lake/domain_reviews.py (2026-10-18), and the conditions below.
COMMON_CRAWL_SOURCE: dict[str, Any] = {
    "id": COMMON_CRAWL_SOURCE_ID,
    "name": "Arsip web Common Crawl",
    "canonical_domain": "commoncrawl.org",
    "category": "dataset",
    "permission_status": PermissionStatus.APPROVED_WITH_CONDITIONS.value,
    "technical_method": "archive_index",
    "connector": "lake_vacancies",
    "connector_config": {},
    "terms_url": "https://commoncrawl.org/terms-of-use",
    "robots_url": None,
    "api_docs_url": "https://commoncrawl.org/columnar-index",
    "decision_reason": (
        "Common Crawl's terms grant a limited licence to use the archive and state that crawled "
        "content remains subject to the site owners' terms. Used for non-commercial research "
        "analytics with conditions: sites whose terms prohibit extraction or were not verified "
        "are excluded (talentscope/lake/domains.py); only structured JobPosting fields are "
        "kept, never page HTML; full descriptions stay in the local lake and are not served by "
        "the API; records are historical observations; owners can opt out. Per-site "
        "default-deny review (2026-10-18, lake/domain_reviews.py): 22 contributing sites, 21 "
        "with terms silent on reuse, 1 permitting copying with a backlink; none grants "
        "republication explicitly."
    ),
    "attribution_text": (
        "Lowongan dari arsip web Common Crawl (commoncrawl.org); hak atas konten tetap milik "
        "situs asal yang ditautkan."
    ),
    "retention_constraints": (
        "Structured JobPosting fields only; no HTML; descriptions not republished."
    ),
    "coverage_note": (
        "Halaman lowongan berdomain .id yang tersimpan di arsip web Common Crawl. Hanya situs "
        "yang sudah ditinjau satu per satu dan tidak melarang pemakaian ulang yang dipakai; "
        "sebagian besar berupa situs info lowongan daerah. Situs yang melarang, belum ditinjau, "
        "atau tidak dapat diperiksa tidak disertakan."
    ),
    "public_label": "Dipakai untuk riset, dengan syarat",
    "public_condition": (
        "Arsip Common Crawl boleh dipakai dengan lisensi terbatas, tetapi isi halamannya tetap "
        "tunduk pada ketentuan situs asal; karena itu kami hanya memakai situs yang sudah "
        "ditinjau dan tidak melarang, hanya menampilkan data ringkas lowongan beserta tautan ke "
        "situs asal, dan menghapus situs yang meminta keluar."
    ),
    "reviewed_at": datetime(2026, 10, 18, tzinfo=timezone.utc),
}


def _matrix_entry_to_fields(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": entry["slug"],
        "name": entry["name"],
        "canonical_domain": entry.get("canonical_domain"),
        "category": entry["category"],
        "permission_status": PermissionStatus(entry["permission_status"]).value,
        "technical_method": entry.get("technical_method") or "unknown",
        "terms_url": entry.get("terms_url"),
        "robots_url": entry.get("robots_url"),
        "api_docs_url": entry.get("api_docs_url"),
        "decision_reason": entry.get("reason"),
        "attribution_text": entry.get("attribution_requirements"),
        "retention_constraints": entry.get("retention_constraints"),
        "reviewed_at": datetime.fromisoformat(entry["reviewed_at"].replace("Z", "+00:00")),
    }


def sync_registry(session: Session, matrix_path: Path | None) -> dict[str, int]:
    """Create or update registry entries from the reviewed research matrix.

    A permission status in the matrix only replaces the stored one when the matrix
    review is newer, so a later, audited decision made with ``set_permission_status``
    is not silently reverted by re-running the sync.
    """
    entries = [LEGACY_SNAPSHOT_SOURCE, COMMON_CRAWL_SOURCE]
    if matrix_path is not None:
        entries += [_matrix_entry_to_fields(e) for e in json.loads(matrix_path.read_text("utf-8"))]

    stats = {"created": 0, "updated": 0}
    for fields in entries:
        source = session.get(Source, fields["id"])
        if source is None:
            session.add(Source(**{"connector_config": {}, **fields}))
            _audit(
                session,
                "registry-sync",
                "source.created",
                fields["id"],
                None,
                {"permission_status": fields["permission_status"]},
            )
            stats["created"] += 1
            continue
        newer_review = source.reviewed_at is None or fields["reviewed_at"] > source.reviewed_at
        for column, value in fields.items():
            if column in ("permission_status", "reviewed_at") and not newer_review:
                continue
            if column == "permission_status" and value != source.permission_status:
                _audit(
                    session,
                    "registry-sync",
                    "source.permission_changed",
                    source.id,
                    "newer policy review in research matrix",
                    {"from": source.permission_status, "to": value},
                )
            setattr(source, column, value)
        stats["updated"] += 1
    session.flush()
    return stats


def set_permission_status(
    session: Session,
    source: Source,
    status: PermissionStatus,
    *,
    actor: str,
    reason: str,
    evidence_url: str,
) -> None:
    """Record an eligibility decision. Requires a reason and evidence, always audited."""
    if not reason.strip() or not evidence_url.strip():
        raise ValueError("a permission change needs a reason and an evidence URL")
    previous = source.permission_status
    source.permission_status = status.value
    source.reviewed_at = datetime.now(timezone.utc)
    source.decision_reason = reason
    _audit(
        session,
        actor,
        "source.permission_changed",
        source.id,
        reason,
        {"from": previous, "to": status.value, "evidence_url": evidence_url},
    )


def set_paused(session: Session, source: Source, paused: bool, *, actor: str, reason: str) -> None:
    """Pause or resume collection. Resuming never makes an ineligible source runnable."""
    if not paused and not can_resume(source):
        raise PermissionError(
            f"source {source.id!r} is {source.permission_status}; "
            "record an approval before resuming"
        )
    source.is_paused = paused
    _audit(session, actor, "source.paused" if paused else "source.resumed", source.id, reason, {})


def _audit(
    session: Session,
    actor: str,
    action: str,
    entity_id: str,
    reason: str | None,
    details: dict[str, Any],
) -> None:
    session.add(
        AuditEvent(
            actor=actor,
            action=action,
            entity_type="source",
            entity_id=entity_id,
            reason=reason,
            details=details,
        )
    )
