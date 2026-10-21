# ADR-0010: Identity and deduplication

**Status:** accepted (2026-10-17)

1. **Within a source**, identity is `(source_id, source_key)`. `source_key` is the
   source's own ID when available, else its canonical URL, else a content fingerprint
   (`source_key_kind` records which). Re-running an import updates `last_seen_at` and
   leaves data unchanged; changed content or a new normalization version updates the job.
2. **Across sources**, a new record is linked to an existing job only when exactly one
   job from another source has the same fingerprint: SHA-256 of normalized title,
   company, and city. Ambiguous or partial matches stay separate, because a wrong merge
   hides a real vacancy (SRS FR-DUP-004). The rule is stored on the record (`match_rule`).
3. **Same-source look-alikes** (same title at one employer) are never merged; they are
   reported in the admin quality view.

Revisit with fuzzy matching only after a second permitted source exists and a reviewed
sample of candidate pairs can measure precision.
