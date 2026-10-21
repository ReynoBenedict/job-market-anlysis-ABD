"""Command-line entry point: ``talentscope <command>``. Run from the repository root."""

from __future__ import annotations

import argparse
import csv
import sys
from importlib.resources import files
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import Session

from talentscope.config import get_settings
from talentscope.db import session_scope
from talentscope.ingestion.http import PoliteClient
from talentscope.ingestion.pipeline import run_source
from talentscope.lake import commands as lake_commands
from talentscope.log_config import configure_logging
from talentscope.models import Source
from talentscope.sources import (
    LEGACY_SNAPSHOT_SOURCE_ID,
    set_paused,
    set_permission_status,
    sync_registry,
)
from talentscope.vocab import PermissionStatus, RunStatus

DEFAULT_MATRIX = Path("docs/research/source_matrix.json")


def _alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(files("talentscope") / "migrations"))
    config.set_main_option("sqlalchemy.url", get_settings().database_url)
    return config


def cmd_db_upgrade(_: argparse.Namespace) -> int:
    command.upgrade(_alembic_config(), "head")
    print("Database schema is up to date.")
    return 0


def cmd_sources_sync(args: argparse.Namespace) -> int:
    matrix = args.matrix if args.matrix.exists() else None
    if matrix is None:
        print(f"warning: {args.matrix} not found; only the built-in snapshot source is registered")
    with session_scope() as session:
        stats = sync_registry(session, matrix)
    print(f"Source registry synced: {stats['created']} created, {stats['updated']} updated.")
    return 0


def cmd_sources_list(_: argparse.Namespace) -> int:
    with session_scope() as session:
        for source in session.scalars(select(Source).order_by(Source.permission_status, Source.id)):
            flags = " (paused)" if source.is_paused else ""
            connector = source.connector or "-"
            print(f"{source.id:<34} {source.permission_status:<28} connector={connector}{flags}")
    return 0


def _get_source(session: Session, source_id: str) -> Source:
    source = session.get(Source, source_id)
    if source is None:
        raise SystemExit(f"unknown source {source_id!r}; run `talentscope sources list`")
    return source


def cmd_sources_set_status(args: argparse.Namespace) -> int:
    with session_scope() as session:
        source = _get_source(session, args.source)
        set_permission_status(
            session,
            source,
            PermissionStatus(args.status),
            actor=args.actor,
            reason=args.reason,
            evidence_url=args.evidence_url,
        )
    print(f"{args.source} is now {args.status}.")
    return 0


def cmd_sources_pause(args: argparse.Namespace) -> int:
    with session_scope() as session:
        set_paused(
            session,
            _get_source(session, args.source),
            args.paused,
            actor=args.actor,
            reason=args.reason,
        )
    print(f"{args.source} {'paused' if args.paused else 'resumed'}.")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    settings = get_settings()
    with (
        session_scope() as session,
        PoliteClient(contact_url=settings.crawler_contact_url) as client,
    ):
        source = _get_source(session, args.source)
        run = run_source(
            session, source, client=client, trigger="cli", max_records=args.max_records
        )
        print(
            f"Run {run.id}: {run.status}"
            f" | seen {run.records_seen}, created {run.records_created},"
            f" updated {run.records_updated},"
            f" unchanged {run.records_unchanged}, rejected {run.records_rejected},"
            f" cross-source matches {run.cross_source_matches}"
        )
        if run.message:
            print(f"  {run.error_category}: {run.message}")
        return 0 if run.status == RunStatus.SUCCEEDED.value else 1


def cmd_bootstrap(args: argparse.Namespace) -> int:
    """Migrate, register sources, and import the historical snapshot. Safe to repeat."""
    cmd_db_upgrade(args)
    cmd_sources_sync(args)
    args.source, args.max_records = LEGACY_SNAPSHOT_SOURCE_ID, None
    return cmd_ingest(args)


def cmd_roles_sample(args: argparse.Namespace) -> int:
    """Write a seeded random sample of app job titles for blind labelling (no predictions)."""
    from sqlalchemy import func

    from talentscope.models import Job

    with session_scope() as session:
        session.execute(select(func.setseed(args.seed)))
        rows = session.execute(
            select(Job.id, Job.title, Job.primary_source_id)
            .order_by(func.random())
            .limit(args.size)
        ).all()
    with args.out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["job_id", "title", "source", "reviewer_a", "reviewer_b", "adjudicated"])
        writer.writerows([str(job_id), title, source, "", "", ""] for job_id, title, source in rows)
    print(f"wrote {len(rows)} titles to {args.out} (seed {args.seed})")
    return 0


def cmd_roles_score(args: argparse.Namespace) -> int:
    from talentscope.normalization.role_evaluation import evaluate, read_labels

    result = evaluate(read_labels(args.labels))
    print(
        f"taxonomy {result.taxonomy_version}: {result.titles} titles"
        f" | coverage {result.coverage:.1%} | precision {result.precision:.1%}"
        f" | recall {result.recall:.1%} | accuracy {result.accuracy:.1%}"
        f" | reviewer agreement {result.reviewer_agreement:.1%} (kappa {result.cohen_kappa:.2f})"
    )
    print(
        f"{'family':<24}{'support':>8}{'predicted':>10}{'correct':>8}{'precision':>10}{'recall':>8}"
    )

    def fmt(value: float | None) -> str:
        return "-" if value is None else f"{value:.0%}"

    for code, score in sorted(result.families.items(), key=lambda item: -item[1].support):
        print(
            f"{code:<24}{score.support:>8}{score.predicted:>10}{score.correct:>8}"
            f"{fmt(score.precision):>10}{fmt(score.recall):>8}"
        )
    print("errors (title | predicted | label):")
    for title, predicted, label in result.confusions:
        print(f"  {title} | {predicted} | {label}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="talentscope", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    db = sub.add_parser("db", help="database schema").add_subparsers(
        dest="db_command", required=True
    )
    db.add_parser("upgrade", help="apply migrations").set_defaults(func=cmd_db_upgrade)

    boot = sub.add_parser("bootstrap", help="migrate, sync sources, import the historical snapshot")
    boot.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    boot.set_defaults(func=cmd_bootstrap)

    sources = sub.add_parser("sources", help="source registry").add_subparsers(
        dest="sources_command", required=True
    )
    sync = sources.add_parser("sync", help="load reviewed decisions from the research matrix")
    sync.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    sync.set_defaults(func=cmd_sources_sync)
    sources.add_parser("list", help="list sources and their status").set_defaults(
        func=cmd_sources_list
    )

    status = sources.add_parser("set-status", help="record an eligibility decision (audited)")
    status.add_argument("source")
    status.add_argument("status", choices=[s.value for s in PermissionStatus])
    status.add_argument("--reason", required=True)
    status.add_argument("--evidence-url", required=True)
    status.add_argument("--actor", required=True, help="who made the decision")
    status.set_defaults(func=cmd_sources_set_status)

    for name, paused in (("pause", True), ("resume", False)):
        toggle = sources.add_parser(name, help=f"{name} an approved source (audited)")
        toggle.add_argument("source")
        toggle.add_argument("--reason", required=True)
        toggle.add_argument("--actor", required=True)
        toggle.set_defaults(func=cmd_sources_pause, paused=paused)

    ingest = sub.add_parser("ingest", help="run a source's connector (policy-gated)")
    ingest.add_argument("source")
    ingest.add_argument("--max-records", type=int, default=None)
    ingest.set_defaults(func=cmd_ingest)

    roles = sub.add_parser("roles", help="evaluate the role taxonomy").add_subparsers(
        dest="roles_command", required=True
    )
    sample = roles.add_parser("sample", help="write a blind labelling sample (CSV)")
    sample.add_argument("--size", type=int, default=200)
    sample.add_argument("--seed", type=float, default=0.42, help="PostgreSQL setseed value, -1..1")
    sample.add_argument("--out", type=Path, required=True)
    sample.set_defaults(func=cmd_roles_sample)
    score = roles.add_parser("score", help="score the taxonomy against labelled CSV")
    score.add_argument("--labels", type=Path, required=True)
    score.set_defaults(func=cmd_roles_score)

    lake_commands.register(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
