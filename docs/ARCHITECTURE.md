# Architecture

```
            docs/research/source_matrix.json      data/raw/glints_jobs.csv (read-only)
                         │                                    │
                talentscope sources sync          talentscope ingest / bootstrap
                         │                                    │
                         ▼                                    ▼
 ┌──────────────────────────── backend/talentscope ─────────────────────────────┐
 │ sources.py ── registry + audited status changes                              │
 │ ingestion/                                                                    │
 │   policy.py ──── gate: only APPROVED*/unpaused/reviewed sources run           │
 │   connectors/ ── legacy_glints_csv (file) · lever (API, disabled)             │
 │   http.py ────── PoliteClient: robots.txt, UA, 5 s/host, backoff, stop on 403 │
 │   pipeline.py ── run record → normalize → upsert → dedupe → run summary       │
 │ normalization/ ─ salary · location · attributes · role_family · job (pure)    │
 │ models.py ────── sources · ingestion_runs · source_records · jobs · audit     │
 │ analytics/ ───── shared filters · search · breakdowns · salary · quality      │
 │ api/ ─────────── FastAPI: /api/v1 public + /api/v1/admin (bearer token)       │
 └───────────────────────────────┬──────────────────────────────────────────────┘
                                 │ SQL (SQLAlchemy 2, Alembic migrations)
                          PostgreSQL 16 (pg_trgm)
                                 ▲
                                 │ JSON over HTTP (server side only)
 ┌──────────────────────────── frontend (Next.js 16) ───────────────────────────┐
 │ Server components fetch per request (connection()), URL holds filter state   │
 │ / · /ringkasan · /lowongan · /lowongan/[id] · /gaji · /pasar · /keterampilan  │
 │ /tersimpan (localStorage) · /sumber-data · /metodologi                        │
 │ /admin/* behind proxy.ts Basic auth; server actions re-check auth            │
 └──────────────────────────────────────────────────────────────────────────────┘

 lake/ (LAKE_DIR, git-ignored) ────────── bronze/silver/gold Parquet built by `talentscope lake ...`
                                         (DuckDB, batch only; never on the request path)
 analytics/evaluate_title_clustering.py ─ PySpark batch job (offline, never on request path)
 legacy/academic_pipeline/ ────────────── original academic scripts, kept for history
```

## Request flow (job search)
1. Browser requests `/lowongan?q=data&province=Banten`.
2. The Next.js server renders the page shell and, inside `<Suspense>`, calls the API
   (`GET /api/v1/jobs`, `/filters`, `/market/overview`) with `API_BASE_URL`.
3. FastAPI validates parameters (`JobFilters`, bounded page size), builds one SQL query
   with the shared filter builder, and returns `{items, page, total, ...}` with
   `{code, label}` pairs for categories.
4. Filter controls are client components; changing one updates the URL inside a React
   transition (optimistic UI), and the server re-renders results.

## Ingestion flow
`run_source` → policy gate (refused runs are recorded) → `build_connector` →
`run_connector`: create run → `fetch()` → `normalize_source_job` (rejects without title)
→ upsert by `(source, source_key)` → cross-source exact match → counts committed every
250 records → final status `SUCCEEDED | PARTIAL | FAILED | REFUSED` with an error
category (`ACCESS_DENIED`, `RATE_LIMITED`, `NETWORK`, `SCHEMA_CHANGED`,
`INVALID_RECORDS`, `POLICY_BLOCKED`, `INTERNAL`).

## Bulk data flow (lake)
`lake discover` (Common Crawl columnar index → candidate pages) → `lake collect`
(rate-limited range requests → bronze JobPosting JSON with provenance) → `lake silver`
(parse, validate, extract skills, deduplicate into canonical vacancies) → `lake gold`
(analytics tables + report.json) → `lake publish` (the `lake_vacancies` connector feeds
canonical vacancies through the ingestion flow above, so the API is unchanged).
Licensed exports enter at bronze through `lake import-jsonl`. Silver applies the per-site
review (default deny) before anything reaches the app. Details: docs/LAKE.md, ADR-0015,
docs/data-engineering/.

**Missing jobs:** the web proxy (`frontend/src/proxy.ts`) checks a job ID with the API
before a full page load and answers unknown IDs with HTTP 404 and the not-found page
(a streamed page cannot change its status afterwards). If the API is unreachable it lets
the page render its own error state with a retry link.

## Module boundaries
- `normalization` imports nothing from the database or web layers; it is unit-tested alone.
- Connectors only yield `SourceJob`; they cannot write to the database.
- `analytics` is the only module that builds read queries; the API maps results to schemas.
- `lake` reads and writes files only; its one path into PostgreSQL is `lake publish`
  through the normal policy-gated pipeline.
- The frontend has no business rules beyond presentation; labels come from the API.

See `docs/adr/` for the decisions and alternatives behind this design.
