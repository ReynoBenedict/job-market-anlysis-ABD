# ADR-0015: File-based data lake (Parquet + DuckDB), Common Crawl as the first bulk source

**Status:** accepted (2026-10-17). Partly supersedes ADR-0008 (analytics engine) and
ADR-0009 (storage); ADR-0011's skill baseline is now implemented in the lake.

## Context
The goal moved from a 1,133-row snapshot to collecting and analysing a large volume of
real Indonesian vacancies. Every job board and government portal reviewed in
docs/RESEARCH_SOURCES.md is blocked or needs written permission for automated
collection. Volume therefore has to come from a source whose terms permit bulk use, and
the pipeline must keep raw observations, survive interruptions, and scale past what is
comfortable in PostgreSQL row-by-row.

## Decisions

### 1. Source: Common Crawl's web archive, `.id` pages with schema.org JobPosting
- Common Crawl's terms grant a licence to use the archive while stating that crawled
  content stays subject to each site owner's terms. We exclude sites whose terms
  prohibit extraction or could not be verified (talentscope/lake/domains.py), keep only
  the structured JobPosting fields, and never serve full descriptions.
- Discovery uses the columnar URL index (remote Parquet via DuckDB httpfs), which Common
  Crawl recommends over its CDX server. Only matching records are fetched, one HTTP range
  request per page; whole WARC files (≈1 GB each) are never downloaded. That matters on
  this machine (≈16–22 GB free disk).
- Rejected or deferred: Web Data Commons' JobPosting subset (same underlying archive,
  pre-extracted; its server was unreachable on 2026-10-17); scraping boards directly
  (prohibited); licensed feeds (cost, see docs/SOURCE_ACQUISITION.md).

### 2. Storage: Parquet files in bronze / silver / gold
- **Bronze:** append-only, one Parquet file per fetched batch (written to a temp name, then
  renamed). Holds the extracted JobPosting JSON plus provenance (crawl, WARC file and
  offset, capture time, content digest, connector version). Never rewritten.
- **Silver:** rebuilt from bronze, incrementally. One observations file per bronze file
  (deterministic names → idempotent). A parser or skill-dictionary version change
  triggers a full reparse.
- **Gold:** rebuilt from silver: analytics tables and report.json.
- PostgreSQL remains the application store; `lake publish` loads canonical vacancies
  through the existing policy-gated pipeline, so the app and API are unchanged.

### 3. Processing engine: DuckDB, with Spark kept as a documented scale-out path
Measured on this laptop (20 logical CPUs, 32 GB RAM) with **synthetic** data shaped like
silver records (docs/BENCHMARKS.md):

| Rows | DuckDB aggregate | DuckDB dedupe | Spark local aggregate | Spark local dedupe |
|---|---|---|---|---|
| 500,000 | 0.09 s / 110 MB | 0.38 s / 206 MB | 2.01 s / 1.2 GB | 1.46 s / 1.4 GB |
| 1,000,000 | 0.17 s / 132 MB | 0.70 s / 334 MB | 2.22 s / 1.8 GB | 2.11 s / 2.2 GB |
| 5,000,000 | 0.45 s / 183 MB | 2.97 s / 939 MB | 4.50 s / 2.4 GB | 5.81 s / 3.8 GB |

Spark also needs about 6 s to start a session. DuckDB is faster and uses less memory at
every size measured; the gap narrows as data grows (dedupe 2× at 5M rows). Spark
pays off when data no longer fits one machine's disk/memory or when a cluster exists.
The benchmark runs the same SQL on both engines, so the migration path is concrete.

### 4. Orchestration: CLI commands, no orchestrator yet
`lake discover → collect → silver → gold → publish` are idempotent CLI steps with
on-disk checkpoints; a shell loop or cron schedules them. Airflow/Dagster/Prefect would
add a service and a metadata DB to orchestrate five linear steps (revisit with several
sources or backfill SLAs).

## Consequences
- Throughput is bounded by Common Crawl's rate limits, not by our compute: an early run
  at 8 requests/s was blocked (HTTP 403 from CloudFront rate-limit rules) within
  minutes. The collector now stops on 403/429 and defaults to 1–2 requests/s.
- Coverage is biased toward sites that publish JobPosting markup on `.id` domains,
  dominated by regional vacancy blogs; large portals are excluded by policy.
- Revisit Spark when bronze exceeds what one machine can process in minutes, or if
  WARC-scale processing (whole crawl segments) becomes necessary.
