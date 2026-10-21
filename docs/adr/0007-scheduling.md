# ADR-0007: Scheduling and orchestration

**Status:** accepted (2026-10-17)

With zero runnable live sources, there is nothing to schedule. Runs are started with
`talentscope ingest <source>`; every run is recorded in `ingestion_runs`, including
refusals by the policy gate.

When a source is approved, the first step is a system cron / GitHub Actions schedule
calling the same CLI command. Airflow, Prefect, or Dagster are rejected for now: they
add a service and a metadata database to orchestrate a single linear step. Revisit when
there are several sources with dependencies, backfills, or SLAs.
