# Ingestion pipeline: operation and recovery

All commands run from the repository root with `DATABASE_URL` set (see `.env.example`).

| Command | Effect |
|---|---|
| `talentscope db upgrade` | Apply Alembic migrations |
| `talentscope sources sync [--matrix docs/research/source_matrix.json]` | Register/refresh sources from the research matrix (newer reviews only) |
| `talentscope sources list` | Show sources, status, connector, paused flag |
| `talentscope ingest <source> [--max-records N]` | Run one source through the policy gate and pipeline |
| `talentscope bootstrap` | `db upgrade` + `sources sync` + import the historical snapshot |
| `talentscope sources pause|resume <source> --reason ... --actor ...` | Operational toggle (audited; resume only for approved sources) |
| `talentscope sources set-status <source> <STATUS> --reason --evidence-url --actor` | Eligibility decision (audited) |

Exit code is 0 only when the run `SUCCEEDED`.

## Run outcomes
| Status | Meaning |
|---|---|
| SUCCEEDED | All fetched records accepted; `details.empty_result=true` when zero records |
| PARTIAL | Some records stored, then a connector error or some rejected records |
| FAILED | Nothing stored (error category says why) |
| REFUSED | Policy gate refused before any request: blocked, unreviewed, paused, or no connector |

Error categories separate *access denied* (401/403, robots disallow: stop, do not retry),
*rate limited*, *network*, *schema changed* (unexpected payload or missing columns),
*invalid records*, and *internal* (bugs, re-raised after the run is recorded).

## Idempotency and re-normalization
- Records are keyed by `(source_id, source_key)`; re-running the same input leaves rows
  unchanged and only extends `last_seen_at` (never moves it backwards).
- Changing normalization rules: bump `NORMALIZATION_VERSION` in
  `normalization/job.py` (or `ROLE_TAXONOMY_VERSION`), then re-run the import; every row
  is re-normalized from its stored source fields and the version is recorded per row.

## Adding a connector
1. Record the source's policy review in the research matrix and registry.
2. Implement `Connector` in `ingestion/connectors/<name>.py`, yielding `SourceJob`s with
   the source's own IDs and URLs. Use `PoliteClient` for all HTTP.
3. Register it in `ingestion/connectors/__init__.py:build_connector`.
4. Add parser tests with synthetic fixtures (empty page, schema change, pagination).
5. Configure the source (`connector`, `connector_config`) and approve it with evidence.

## Freshness policy
`POTENTIALLY_ACTIVE` if seen within `FRESHNESS_WINDOW_DAYS` (default 30) and not past
`expires_at`; `EXPIRED_BY_SOURCE` if past `expires_at`; otherwise `NOT_SEEN_RECENTLY`.
Labels are computed at read time, so they age correctly without a scheduled job.

## Recovery
- A crashed run is marked `FAILED/INTERNAL`; already-committed batches remain and the
  import can simply be re-run (idempotent).
- Database backup: `docker compose exec db pg_dump -U talentscope talentscope > backup.sql`.
  Restore into an empty database with `psql`. The snapshot can always be re-imported
  from `data/raw/glints_jobs.csv`.
