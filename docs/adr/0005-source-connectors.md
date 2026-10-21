# ADR-0005: Source connector framework

**Status:** accepted (2026-10-17)

## Context
Research (docs/RESEARCH_SOURCES.md) found no job-listing source that may be collected
today; the realistic first live sources are documented ATS JSON APIs (Lever, Greenhouse,
Ashby) after per-employer written consent.

## Options
Scrapy vs. a small adapter interface over httpx.

## Decision
A small `Connector` interface (`describe_input`, `observed_at`, `fetch() -> SourceJob`)
plus one shared pipeline that owns policy gating, normalization, upserts, deduplication,
and run reporting. Network access goes through `PoliteClient` (robots.txt check,
identifying User-Agent, >=5 s per-host spacing, bounded retries with backoff,
Retry-After, stop on 401/403/robots disallow, response size cap).

Implemented connectors: `legacy_glints_csv` (file import) and `lever` (Lever Postings
API; disabled pending consent, tested with synthetic fixtures only).

## Consequences
- Adding an API source is one module plus a registry entry; no pipeline changes.
- Scrapy would add a second runtime model for little gain with JSON APIs. Revisit if an
  approved source needs large HTML crawls with link discovery.
