# Roadmap and remaining work

Prioritized by permission → user value → data availability (SRS §20).

## Done (2026-10-17)
Foundation, canonical model, policy-gated ingestion, idempotent snapshot import,
search/filter/detail, market/salary analytics, honest skills page, source registry,
methodology, admin workspace, Docker Compose, CI definition, tests (see README).

Data lake (2026-10-17): Common Crawl JobPosting collection, bronze/silver/gold Parquet,
deduplication into canonical vacancies, data-quality report, skill dictionary with a
reviewed sample, DuckDB/Spark benchmarks, JSON Lines import path for licensed feeds,
publishing into the app (docs/LAKE.md, docs/DATA_INVENTORY.md).

## Path to 100,000 and 1,000,000 real vacancies
Numbers and the gap: docs/DATA_INVENTORY.md; source-by-source matrix:
docs/data-engineering/SOURCE_ASSESSMENT.md. Order of leverage:
0. **Data request to Kemnaker (Pusat Pasar Kerja) for Karirhub/SIAPkerja vacancies**: the
   national reporting system (press: 753,500 vacancies Jan–Sep 2025), current listings
   with status at source. The single most valuable permission.
1. **Licensed Indonesia feed** (Techmap per-country files, Lightcast, or TheirStack):
   the only route to 1M and the fastest to 100k. Needs a budget decision and a check of
   redistribution terms; then register it and run `talentscope lake import-jsonl`.
   Cost and licence are blockers for the project owner, not engineering work.
2. **Continue polite Common Crawl collection** across past crawls (2019–2026) with the
   existing `lake collect` loop at ≤1–2 requests/s. Expected yield per crawl and the
   overlap between crawls are measured in DATA_INVENTORY.md; it is weeks of wall-clock
   time, not compute.
3. **Web Data Commons JobPosting subset** once its server is reachable: adds Indonesian
   vacancies on non-`.id` domains (needs a small N-Quads reader feeding bronze).
4. **Written permission** from Kemnaker (Pasker ID/Karirhub), Kalibrr, Pintarnya,
   Karir.com, Dealls (letters outlined in RESEARCH_SOURCES.md §4); each becomes a source
   through `import-jsonl` or a connector.
5. **Review the top archive sites' terms** before showing individual archived listings
   publicly (RESEARCH_SOURCES.md §6.1).
6. **Re-measure skill precision** for `skills-2026.10.3` with a human annotator, and
   measure recall.
7. When bronze passes what one machine processes in minutes (well beyond 5M records per
   the benchmarks), move silver/gold SQL to Spark (ADR-0015).

## Next (application)
1. **Obtain a permitted live source.** Highest leverage: without it there is no
   freshness, no descriptions, and no skills. Candidates (docs/RESEARCH_SOURCES.md
   §"Recommended connector order"): per-employer consent for Lever/Greenhouse/Ashby
   boards; a data-sharing request to Kemnaker (Pasker ID/Karirhub); partnership requests
   to Kalibrr/Pintarnya/Karir.com/Dealls. The Lever connector is ready; add Greenhouse
   and Ashby adapters (small, same pattern).
2. **Confirm republication rights for the Glints snapshot** before any public deployment,
   or restrict the public site to aggregates (docs/DATA_POLICY.md).
3. **Measure role-taxonomy precision** on a labelled sample of ~150 titles; publish it on
   the methodology page.
4. **Skill analytics in the app:** the lake now extracts skills from archived
   descriptions (gold `skills_overall`, `skills_by_role_family`); expose them on
   `/keterampilan` with denominators and the precision caveat.
5. **Career matching** baseline on top of (4), with explanations and persona-based
   evaluation (ADR-0012).
6. **Scheduled runs** via cron/GitHub Actions for approved sources; history-based trends
   only after several observation dates exist (ADR-0007).
7. **Aggregate open-data import** (Balikpapan vacancies-by-education, the one
   APPROVED_WITH_CONDITIONS dataset) as a separate "official statistics" panel; it is
   aggregate counts, not listings, so it needs its own small table.
8. Accessibility audit (axe + screen reader), and a Lighthouse pass on the production build.
