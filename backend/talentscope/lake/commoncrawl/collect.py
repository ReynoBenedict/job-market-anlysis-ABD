"""Download candidate pages for a crawl into the bronze layer, resumably.

Bronze is append-only: each batch becomes a new Parquet file and nothing is rewritten.
Re-running skips records already fetched, so an interrupted run simply continues.

Three ways to avoid needless requests to Common Crawl:
1. a (warc file, offset) already fetched is never fetched again;
2. a URL whose content digest matches an earlier capture is recorded as a
   *re-observation* (evidence the page still existed in this crawl) without downloading;
3. a domain with no JobPosting markup after ``MIN_DOMAIN_TRIALS`` pages is skipped.
"""

from __future__ import annotations

import json
import logging
import random
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from talentscope.lake.commoncrawl.warc import (
    AccessBlocked,
    ArchiveFetcher,
    Capture,
    FetchFailed,
    RecordPointer,
)
from talentscope.lake.jsonld import extract_job_postings
from talentscope.lake.layout import Lake

logger = logging.getLogger(__name__)

CONNECTOR_VERSION = "commoncrawl-jobposting/1"
BATCH_SIZE = 500
MIN_DOMAIN_TRIALS = 15
SHUFFLE_SEED = 20261017  # interleaves domains so yield tracking learns early, reproducibly
# Failures worth retrying on a later run; anything else is permanent for that record.
TRANSIENT_RESULTS = (
    "network",
    "not_attempted",
    "http_429",
    "http_500",
    "http_502",
    "http_503",
    "http_504",
    "http_403",
)

CAPTURE_SCHEMA = pa.schema(
    [
        ("crawl", pa.string()),
        ("url", pa.string()),
        ("domain", pa.string()),
        ("index_fetch_time", pa.timestamp("us", tz="UTC")),
        ("content_digest", pa.string()),
        ("warc_filename", pa.string()),
        ("warc_record_offset", pa.int64()),
        ("warc_record_length", pa.int64()),
        ("captured_at", pa.timestamp("us", tz="UTC")),
        ("http_status", pa.int32()),
        ("fetch_result", pa.string()),
        ("jobposting_count", pa.int32()),
        ("malformed_jsonld", pa.int32()),
        ("postings_json", pa.string()),
        ("fetched_at", pa.timestamp("us", tz="UTC")),
        ("connector_version", pa.string()),
    ]
)
REOBSERVATION_SCHEMA = pa.schema(
    [
        ("crawl", pa.string()),
        ("url", pa.string()),
        ("domain", pa.string()),
        ("index_fetch_time", pa.timestamp("us", tz="UTC")),
        ("content_digest", pa.string()),
    ]
)


@dataclass
class CollectStats:
    crawl: str
    candidates: int = 0
    already_fetched: int = 0
    reobserved_unchanged: int = 0
    skipped_low_yield_domain: int = 0
    fetched: int = 0
    failures: Counter[str] = field(default_factory=Counter)
    pages_with_postings: int = 0
    postings: int = 0
    seconds: float = 0.0
    blocked: str | None = None


def _glob(path: Path) -> str:
    return (path / "**" / "*.parquet").as_posix()


def _existing(
    con: duckdb.DuckDBPyConnection, lake: Lake, crawl: str
) -> tuple[set[tuple[str, int]], set[tuple[str, str]], dict[str, list[int]]]:
    """Already-fetched records of this crawl, (url, digest) pairs captured in any crawl,
    and per-domain [pages tried, pages with JobPosting]."""
    captures_root = lake.bronze / "commoncrawl" / "captures"
    if not any(captures_root.glob("**/*.parquet")):
        return set(), set(), {}
    pattern = _glob(captures_root)
    fetched = set(
        con.execute(
            f"select warc_filename, warc_record_offset from read_parquet('{pattern}', hive_partitioning=false) "
            f"where crawl = ? and fetch_result not in {TRANSIENT_RESULTS}",
            [crawl],
        ).fetchall()
    )
    seen_content = set(
        con.execute(
            f"select url, content_digest from read_parquet('{pattern}', hive_partitioning=false) where fetch_result = 'ok'"
        ).fetchall()
    )
    yields = {
        domain: [tried, hits]
        for domain, tried, hits in con.execute(
            f"""select domain, count(*), count(*) filter (where jobposting_count > 0)
                from read_parquet('{pattern}', hive_partitioning=false) where fetch_result = 'ok' group by 1"""
        ).fetchall()
    }
    return fetched, seen_content, yields


def _yield_rate(counts: list[int] | None) -> float:
    if not counts or counts[0] == 0:
        return 0.0
    return counts[1] / counts[0]


def _capture_row(
    candidate: dict[str, Any], result: Capture | FetchFailed, fetched_at: datetime
) -> dict[str, Any]:
    row = {
        "crawl": candidate["crawl"],
        "url": candidate["url"],
        "domain": candidate["domain"],
        "index_fetch_time": candidate["fetch_time"],
        "content_digest": candidate["content_digest"],
        "warc_filename": candidate["warc_filename"],
        "warc_record_offset": candidate["warc_record_offset"],
        "warc_record_length": candidate["warc_record_length"],
        "fetched_at": fetched_at,
        "connector_version": CONNECTOR_VERSION,
        "captured_at": None,
        "http_status": None,
        "jobposting_count": 0,
        "malformed_jsonld": 0,
        "postings_json": None,
    }
    if isinstance(result, FetchFailed):
        return {**row, "fetch_result": result.reason}
    postings, malformed = extract_job_postings(result.body)
    return {
        **row,
        "fetch_result": "ok",
        "captured_at": result.captured_at,
        "http_status": result.http_status,
        "jobposting_count": len(postings),
        "malformed_jsonld": malformed,
        # Only the JobPosting objects are retained, never the page HTML.
        "postings_json": json.dumps(postings, ensure_ascii=False) if postings else None,
    }


def collect_crawl(
    lake: Lake, crawl: str, fetcher: ArchiveFetcher, *, max_pages: int | None = None
) -> CollectStats:
    started = time.monotonic()
    stats = CollectStats(crawl=crawl)
    candidates_path = lake.cc_candidates(crawl)
    if not candidates_path.exists():
        raise FileNotFoundError(f"run discovery for {crawl} first ({candidates_path})")

    con = duckdb.connect()
    candidates = (
        con.execute(f"select * from '{candidates_path.as_posix()}'").fetch_arrow_table().to_pylist()
    )
    stats.candidates = len(candidates)
    fetched, seen_content, yields = _existing(con, lake, crawl)
    recorded_reobservations = _existing_reobservations(con, lake, crawl)

    pending, reobserved = [], []
    for candidate in candidates:
        key = (candidate["url"], candidate["content_digest"])
        if (
            candidate["warc_filename"],
            candidate["warc_record_offset"],
        ) in fetched or key in recorded_reobservations:
            stats.already_fetched += 1
        elif key in seen_content:
            reobserved.append(candidate)
        else:
            pending.append(candidate)
    _write_reobservations(lake, crawl, reobserved)
    stats.reobserved_unchanged = len(reobserved)

    random.Random(SHUFFLE_SEED).shuffle(pending)
    # Domains that already produced JobPosting pages go first (highest yield first); the
    # sort is stable, so unknown domains keep their shuffled order for exploration.
    pending.sort(key=lambda c: -_yield_rate(yields.get(c["domain"])))
    out_dir = lake.cc_captures_dir(crawl)
    out_dir.mkdir(parents=True, exist_ok=True)
    budget = max_pages if max_pages is not None else len(pending)

    position = attempted = 0
    while position < len(pending) and attempted < budget:
        batch: list[dict[str, Any]] = []
        while position < len(pending) and len(batch) < min(BATCH_SIZE, budget - attempted):
            candidate = pending[position]
            position += 1
            tried, hits = yields.get(candidate["domain"], [0, 0])
            if tried >= MIN_DOMAIN_TRIALS and hits == 0:
                stats.skipped_low_yield_domain += 1
                continue
            batch.append(candidate)
        if not batch:
            break
        attempted += len(batch)
        pointers = [
            RecordPointer(c["warc_filename"], c["warc_record_offset"], c["warc_record_length"])
            for c in batch
        ]
        rows = []
        fetched_at = datetime.now(timezone.utc)
        results = fetcher.fetch_many(pointers)
        for candidate in batch:
            try:
                _, result = next(results)
            except AccessBlocked as exc:
                stats.blocked = str(exc)
                results.close()  # lets queued workers finish without sending requests
                break
            row = _capture_row(candidate, result, fetched_at)
            rows.append(row)
            if row["fetch_result"] == "ok":
                stats.fetched += 1
                counts = yields.setdefault(candidate["domain"], [0, 0])
                counts[0] += 1
                if row["jobposting_count"]:
                    counts[1] += 1
                    stats.pages_with_postings += 1
                    stats.postings += row["jobposting_count"]
            else:
                stats.failures[row["fetch_result"]] += 1
        if rows:
            # Written under a temporary name and renamed, so readers never see half a file.
            batch_file = out_dir / f"batch-{fetched_at:%Y%m%dT%H%M%S%f}.parquet"
            temporary = batch_file.with_suffix(".tmp")
            pq.write_table(
                pa.Table.from_pylist(rows, schema=CAPTURE_SCHEMA), temporary, compression="zstd"
            )
            temporary.replace(batch_file)
        if stats.blocked:
            logger.error(
                "collection stopped: access blocked",
                extra={"crawl": crawl, "reason": stats.blocked},
            )
            break
        logger.info(
            "batch written",
            extra={
                "crawl": crawl,
                "fetched": stats.fetched,
                "with_postings": stats.pages_with_postings,
                "failures": sum(stats.failures.values()),
            },
        )

    stats.seconds = round(time.monotonic() - started, 1)
    state = lake.state / "commoncrawl"
    state.mkdir(parents=True, exist_ok=True)
    with (state / "collect_runs.jsonl").open("a", encoding="utf-8") as log:
        log.write(
            json.dumps(
                {
                    **asdict(stats),
                    "failures": dict(stats.failures),
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            + "\n"
        )
    return stats


def _existing_reobservations(
    con: duckdb.DuckDBPyConnection, lake: Lake, crawl: str
) -> set[tuple[str, str]]:
    target = lake.bronze / "commoncrawl" / "reobservations" / f"crawl={crawl}"
    if not any(target.glob("*.parquet")):
        return set()
    return set(
        con.execute(
            f"select url, content_digest from read_parquet('{(target / '*.parquet').as_posix()}', hive_partitioning=false)"
        ).fetchall()
    )


def _write_reobservations(lake: Lake, crawl: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    target = lake.bronze / "commoncrawl" / "reobservations" / f"crawl={crawl}"
    target.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(
        [
            {
                "crawl": r["crawl"],
                "url": r["url"],
                "domain": r["domain"],
                "index_fetch_time": r["fetch_time"],
                "content_digest": r["content_digest"],
            }
            for r in rows
        ],
        schema=REOBSERVATION_SCHEMA,
    )
    pq.write_table(
        table, target / f"reobservations-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%f}.parquet"
    )
