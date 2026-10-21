# ADR-0009: Raw data storage and retention

**Status:** accepted (2026-10-17)

- Original files under `data/` are inputs only. Imports open them read-only, and the
  pipeline never writes to `data/`. SHA-256 of each imported file is recorded on the run.
- Each source record stores only the fields the source provides and permits
  (`raw_fields` JSONB), not HTML pages. Descriptions are not stored unless a source's
  permission covers it (`store_description` is off by default for the Lever connector).
- Records not returned by a later run are kept and age out via `last_seen_at`
  (freshness labels), rather than being deleted. Deletion on a source owner's request is
  a manual, audited operation (docs/DATA_POLICY.md).
- Object storage, Parquet exports, and a data lake are not used: there is one 205 KB file.
