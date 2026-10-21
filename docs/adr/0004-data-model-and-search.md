# ADR-0004: Data model and search

**Status:** accepted (2026-10-17)

## Context
SRS §7 separates source records from canonical jobs and asks for provenance, lifecycle
fields, and explicit missing values. The current data has no IDs, URLs, descriptions, or
collection timestamps.

## Decision
Tables: `sources`, `ingestion_runs`, `source_records`, `jobs`, `audit_events`.

- `jobs` holds normalized values *and* the source text they came from (`salary_text`,
  `experience_text`, ...). Missing values are `NULL` or an explicit `UNKNOWN` code, never 0.
  Check constraints enforce `salary_min <= salary_max` and "amounts only when disclosed".
- `source_records` keeps each source's key, URL, raw permitted fields (JSONB), content
  hash, parser version, and first/last run.
- Not modelled yet, deliberately: companies (names are not resolvable to entities),
  skills (data too sparse, ADR-0011), users (no accounts, ADR-0013), snapshots/history
  (one observation exists; `first_seen_at`/`last_seen_at` are kept for when more arrive).

**Search:** every query word must appear (case-insensitive substring) in a precomputed
`search_text` (title, company, location, tags), backed by a `pg_trgm` GIN index.
Relevance ordering uses `word_similarity` against the title. Substring matching handles
mixed Indonesian/English titles and partial words better than a stemmed full-text config
on this data. An external search engine is unjustified at this size.

## Consequences
- `search_text` is maintained by the normalizer (Postgres generated columns cannot use
  `array_to_string`).
- Analytics run as SQL aggregates over `jobs` with the same filter builder as search.
