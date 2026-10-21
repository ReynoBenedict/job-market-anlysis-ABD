"""Import a JSON Lines export of JobPosting objects (licensed feed, permitted partner
export) into bronze, so it flows through the same silver/gold pipeline.

Each line is one schema.org-style JobPosting object plus two provenance fields:
  "url":          the vacancy's canonical URL at the provider (http/https)
  "captured_at":  ISO 8601 time the provider observed the vacancy
Lines missing either are rejected and counted, never imported half-way.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pyarrow as pa
import pyarrow.parquet as pq

from talentscope.lake.commoncrawl.collect import CAPTURE_SCHEMA
from talentscope.lake.layout import Lake

CONNECTOR_VERSION = "jsonl-import/1"
MAX_REJECTION_SAMPLES = 20


@dataclass
class ImportStats:
    source_id: str
    lines: int = 0
    imported: int = 0
    rejected: int = 0
    rejection_samples: list[str] = field(default_factory=list)
    already_imported: bool = False


def imports_dir(lake: Lake, source_id: str) -> Path:
    return lake.bronze / "imports" / source_id


def _row(source_id: str, record: dict[str, Any], digest: str, line_number: int) -> dict[str, Any]:
    url = record.pop("url")
    captured_at = datetime.fromisoformat(str(record.pop("captured_at")).replace("Z", "+00:00"))
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=timezone.utc)
    record.setdefault("@type", "JobPosting")
    return {
        "crawl": f"import:{source_id}",
        "url": url,
        "domain": urlsplit(url).netloc.lower().removeprefix("www."),
        "index_fetch_time": captured_at,
        "content_digest": f"{digest}:{line_number}",
        "warc_filename": None,
        "warc_record_offset": None,
        "warc_record_length": None,
        "captured_at": captured_at,
        "http_status": None,
        "fetch_result": "ok",
        "jobposting_count": 1,
        "malformed_jsonld": 0,
        "postings_json": json.dumps([record], ensure_ascii=False),
        "fetched_at": datetime.now(timezone.utc),
        "connector_version": CONNECTOR_VERSION,
    }


def import_jsonl(lake: Lake, source_id: str, path: Path) -> ImportStats:
    stats = ImportStats(source_id=source_id)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    target = imports_dir(lake, source_id) / f"import-{digest[:16]}.parquet"
    if target.exists():
        stats.already_imported = True
        return stats

    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            stats.lines += 1
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError("line is not a JSON object")
                url = record.get("url")
                if not isinstance(url, str) or urlsplit(url).scheme not in ("http", "https"):
                    raise ValueError("missing or invalid url")
                if "captured_at" not in record:
                    raise ValueError("missing captured_at")
                rows.append(_row(source_id, record, digest, line_number))
            except (ValueError, TypeError) as exc:
                stats.rejected += 1
                if len(stats.rejection_samples) < MAX_REJECTION_SAMPLES:
                    stats.rejection_samples.append(f"line {line_number}: {exc}")
    stats.imported = len(rows)
    if rows:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".tmp")
        table = pa.Table.from_pylist(rows, schema=CAPTURE_SCHEMA)
        pq.write_table(table, temporary, compression="zstd")
        temporary.replace(target)
    return stats
