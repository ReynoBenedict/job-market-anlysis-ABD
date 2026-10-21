"""`talentscope lake ...` commands: the batch pipeline from archive to analytics."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from talentscope.config import get_settings
from talentscope.db import session_scope
from talentscope.ingestion.http import PoliteClient
from talentscope.ingestion.pipeline import run_source
from talentscope.ingestion.policy import PolicyRefusal, ensure_runnable
from talentscope.lake.commoncrawl import discovery
from talentscope.lake.commoncrawl.collect import CONNECTOR_VERSION, CollectStats, collect_crawl
from talentscope.lake.commoncrawl.warc import (
    DEFAULT_REQUESTS_PER_SECOND,
    DEFAULT_WORKERS,
    ArchiveFetcher,
)
from talentscope.lake.gold import build_gold
from talentscope.lake.imports import import_jsonl
from talentscope.lake.layout import Lake
from talentscope.lake.silver import build_silver
from talentscope.models import IngestionRun, Source
from talentscope.sources import COMMON_CRAWL_SOURCE_ID
from talentscope.vocab import RunErrorCategory, RunStatus

logger = logging.getLogger(__name__)


def _lake() -> Lake:
    lake = Lake(get_settings().lake_dir)
    lake.ensure()
    return lake


def _crawls(args: argparse.Namespace) -> list[str]:
    if args.crawl:
        return list(args.crawl)
    return discovery.list_crawls()[: args.newest]


def _check_policy() -> None:
    """Refuse to touch Common Crawl unless its registry entry is runnable."""
    with session_scope() as session:
        source = session.get(Source, COMMON_CRAWL_SOURCE_ID)
        if source is None:
            raise SystemExit("Common Crawl is not registered; run `talentscope sources sync` first")
        try:
            ensure_runnable(source, mode="collect")
        except PolicyRefusal as refusal:
            raise SystemExit(f"refused by source policy: {refusal}") from refusal


def _record_run(stats: CollectStats, started_at: datetime) -> None:
    failures = sum(stats.failures.values())
    if stats.blocked:
        status = RunStatus.PARTIAL if stats.fetched else RunStatus.FAILED
        category = RunErrorCategory.ACCESS_DENIED
    elif stats.fetched == 0 and failures:
        status, category = RunStatus.FAILED, RunErrorCategory.NETWORK
    elif failures:
        status, category = RunStatus.PARTIAL, RunErrorCategory.NETWORK
    else:
        status, category = RunStatus.SUCCEEDED, None
    with session_scope() as session:
        session.add(
            IngestionRun(
                source_id=COMMON_CRAWL_SOURCE_ID,
                trigger="cli",
                mode="collect",
                status=status.value,
                error_category=category.value if category else None,
                message=stats.blocked
                or (f"{failures} archived pages could not be fetched" if failures else None),
                parser_version=CONNECTOR_VERSION,
                input_reference=f"Common Crawl {stats.crawl} (.id job-like pages)",
                observed_at=started_at,
                records_seen=stats.candidates,
                records_created=stats.pages_with_postings,
                records_unchanged=stats.reobserved_unchanged + stats.already_fetched,
                records_rejected=stats.skipped_low_yield_domain,
                details={
                    "fetched": stats.fetched,
                    "postings": stats.postings,
                    "failures": dict(stats.failures),
                    "skipped_low_yield_domain": stats.skipped_low_yield_domain,
                    "seconds": stats.seconds,
                    "note": "records_created = archived pages with JobPosting markup (bronze)",
                },
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
            )
        )


def cmd_discover(args: argparse.Namespace) -> int:
    _check_policy()
    lake = _lake()
    con = discovery.connect()
    for crawl in _crawls(args):
        output = lake.cc_candidates(crawl)
        if output.exists() and not args.force:
            print(f"{crawl}: candidates exist, skipping (use --force to rediscover)")
            continue
        stats = discovery.discover(con, crawl, output)
        print(
            f"{crawl}: {stats.tld_pages:,} .id pages, {stats.job_like_pages:,} job-like, "
            f"{stats.excluded_by_domain_policy:,} excluded by domain policy, "
            f"{stats.candidates:,} candidates ({stats.seconds}s)"
        )
    return 0


def cmd_collect(args: argparse.Namespace) -> int:
    _check_policy()
    lake = _lake()
    settings = get_settings()
    fetcher = ArchiveFetcher(
        contact_url=settings.crawler_contact_url, workers=args.workers, requests_per_second=args.rps
    )
    try:
        for crawl in _crawls(args):
            if not lake.cc_candidates(crawl).exists():
                stats_d = discovery.discover(discovery.connect(), crawl, lake.cc_candidates(crawl))
                print(f"{crawl}: discovered {stats_d.candidates:,} candidates")
            started_at = datetime.now(timezone.utc)
            stats = collect_crawl(lake, crawl, fetcher, max_pages=args.max_pages)
            _record_run(stats, started_at)
            print(
                f"{crawl}: fetched {stats.fetched:,} pages ({stats.pages_with_postings:,} with "
                f"JobPosting, {stats.postings:,} postings), {stats.reobserved_unchanged:,} unchanged "
                f"re-observations, {stats.already_fetched:,} already done, "
                f"{stats.skipped_low_yield_domain:,} skipped (no-yield domains), "
                f"failures {dict(stats.failures)} in {stats.seconds}s"
            )
            if stats.blocked:
                print(
                    f"STOPPED: {stats.blocked}. Common Crawl asks clients to slow down; wait before "
                    "retrying and lower --rps/--workers. Remaining crawls were not attempted."
                )
                return 2
    finally:
        fetcher.close()
    return 0


def cmd_silver(args: argparse.Namespace) -> int:
    stats = build_silver(_lake(), full=args.full)
    print(
        f"silver: {stats.bronze_files_parsed} new bronze files parsed; {stats.observations:,} observations "
        f"({stats.valid_observations:,} valid), {stats.source_records:,} source records, "
        f"{stats.vacancies:,} canonical vacancies ({stats.seconds}s)"
    )
    return 0


def cmd_gold(_: argparse.Namespace) -> int:
    report = build_gold(_lake())
    inventory = report["inventory"]
    print(
        f"gold: {inventory['canonical_vacancies']:,} vacancies from {inventory['distinct_sites']:,} sites, "
        f"{inventory['distinct_employers']:,} employers; report at {get_settings().lake_dir / 'gold' / 'report.json'}"
    )
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    """Load silver vacancies into the app database through the normal, policy-gated pipeline.

    Each registry source publishes the vacancies whose representative record it supplied.
    The run is a complete snapshot: it is applied in one transaction, and vacancies silver
    no longer contains (merged by a rebuild, or from a newly excluded site) are retired in
    that same transaction. A failed run publishes nothing (see ingestion/pipeline.py).
    """
    source_id = getattr(args, "source", None) or COMMON_CRAWL_SOURCE_ID
    with (
        session_scope() as session,
        PoliteClient(contact_url=get_settings().crawler_contact_url) as client,
    ):
        source = session.get(Source, source_id)
        if source is None:
            raise SystemExit(
                f"source {source_id!r} is not registered; run `talentscope sources sync` first"
            )
        run = run_source(session, source, client=client, trigger="cli")
        print(
            f"publish: {run.status} | seen {run.records_seen:,}, created {run.records_created:,}, "
            f"updated {run.records_updated:,}, unchanged {run.records_unchanged:,}, rejected {run.records_rejected:,}"
        )
        if run.status != RunStatus.SUCCEEDED.value:
            print(f"publish: {run.message}")
            return 1
        print(
            f"publish: retired {run.details.get('retired_records', 0):,} superseded records "
            f"({run.details.get('retired_jobs', 0):,} jobs removed)"
        )
        return 0


def cmd_import_jsonl(args: argparse.Namespace) -> int:
    """Load a licensed/permitted JSON Lines export into bronze (policy-gated)."""
    with session_scope() as session:
        source = session.get(Source, args.source)
        if source is None:
            raise SystemExit(f"unknown source {args.source!r}; register it with its licence first")
        try:
            ensure_runnable(source, mode="import")
        except PolicyRefusal as refusal:
            raise SystemExit(f"refused by source policy: {refusal}") from refusal
    stats = import_jsonl(_lake(), args.source, args.file)
    if stats.already_imported:
        print(f"{args.file} was already imported for {args.source}; nothing to do")
        return 0
    print(f"imported {stats.imported:,} of {stats.lines:,} lines; rejected {stats.rejected:,}")
    for sample in stats.rejection_samples:
        print(f"  {sample}")
    return 0 if stats.rejected == 0 else 1


def cmd_run(args: argparse.Namespace) -> int:
    """The repeatable processing sequence after collection: silver -> gold -> publish."""
    cmd_silver(args)
    cmd_gold(args)
    return cmd_publish(args) if args.publish else 0


def cmd_report(_: argparse.Namespace) -> int:
    path = get_settings().lake_dir / "gold" / "report.json"
    if not path.exists():
        raise SystemExit(f"{path} not found; run `talentscope lake gold` first")
    report = json.loads(path.read_text("utf-8"))
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "inventory",
                    "completeness_of_vacancies",
                    "time_coverage",
                    "source_mix",
                    "top10_sites_share",
                )
            },
            indent=2,
        )
    )
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    from talentscope.lake.benchmark import run_benchmark

    result = run_benchmark(_lake(), args.sizes, with_spark=not args.no_spark)
    for m in result["measurements"]:  # type: ignore[attr-defined]
        print(
            f"{m['engine']:<12} {m['rows']:>10,} {m['workload']:<10} {m['seconds']:>9.3f}s  peak {m['peak_rss_mb']:,.0f} MB"
        )
    return 0


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    lake = subparsers.add_parser(
        "lake", help="data lake pipeline (Common Crawl -> bronze -> silver -> gold)"
    )
    commands = lake.add_subparsers(dest="lake_command", required=True)

    def crawl_selection(parser: argparse.ArgumentParser) -> None:
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--crawl", action="append", help="crawl ID, e.g. CC-MAIN-2026-39 (repeatable)"
        )
        group.add_argument("--newest", type=int, help="the N most recent crawls")

    discover = commands.add_parser("discover", help="find candidate job pages in the URL index")
    crawl_selection(discover)
    discover.add_argument(
        "--force", action="store_true", help="rediscover even if candidates exist"
    )
    discover.set_defaults(func=cmd_discover)

    collect = commands.add_parser(
        "collect", help="download candidate pages into bronze (resumable)"
    )
    crawl_selection(collect)
    collect.add_argument(
        "--max-pages", type=int, default=None, help="cap on pages fetched per crawl"
    )
    collect.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    collect.add_argument(
        "--rps",
        type=float,
        default=DEFAULT_REQUESTS_PER_SECOND,
        help="max requests per second to Common Crawl (stay low: CloudFront rate-limits)",
    )
    collect.set_defaults(func=cmd_collect)

    silver = commands.add_parser(
        "silver", help="bronze -> silver (incremental; --full to reparse everything)"
    )
    silver.add_argument("--full", action="store_true")
    silver.set_defaults(func=cmd_silver)
    commands.add_parser("gold", help="silver -> gold analytics tables and report").set_defaults(
        func=cmd_gold
    )
    publish = commands.add_parser("publish", help="load silver vacancies into the app database")
    publish.add_argument(
        "--source", default=None, help=f"registry source (default {COMMON_CRAWL_SOURCE_ID})"
    )
    publish.set_defaults(func=cmd_publish)

    importer = commands.add_parser(
        "import-jsonl", help="load a licensed/permitted JobPosting JSON Lines export"
    )
    importer.add_argument("--source", required=True, help="registry source id (must be approved)")
    importer.add_argument("--file", type=Path, required=True)
    importer.set_defaults(func=cmd_import_jsonl)

    run = commands.add_parser("run", help="silver -> gold, and optionally publish to the app")
    run.add_argument("--full", action="store_true", help="reparse all bronze files")
    run.add_argument("--publish", action="store_true")
    run.set_defaults(func=cmd_run)
    commands.add_parser("report", help="print the inventory from gold/report.json").set_defaults(
        func=cmd_report
    )

    bench = commands.add_parser(
        "benchmark", help="DuckDB vs Spark on SYNTHETIC data (needs the bench extra)"
    )
    bench.add_argument("--sizes", type=int, nargs="+", default=[10_000, 100_000, 1_000_000])
    bench.add_argument("--no-spark", action="store_true")
    bench.set_defaults(func=cmd_benchmark)
