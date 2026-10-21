# Source acquisition: feasibility of 100,000 → 1,000,000 real Indonesian vacancies

Status as of 2026-10-17/18. Policy background: [RESEARCH_SOURCES.md](RESEARCH_SOURCES.md)
(27 sources, per-source evidence). Measured results: [DATA_INVENTORY.md](DATA_INVENTORY.md).
Not legal advice.

## Short answers

1. **Can we realistically reach 100,000 unique Indonesian vacancies?** Not from sources
   usable today in the time available. The one usable bulk source (Common Crawl's
   archive of `.id` job pages) yields a few thousand to ~15,000 new JobPosting pages per
   crawl, and Common Crawl's rate limits cap us at ~1–2 pages/s. Reaching 100k from it
   is plausible over several weeks of polite collection across past crawls
   (estimate below), not overnight. A licensed feed would reach it immediately.
2. **Can we realistically reach 1,000,000?** Only with licensed data (or written
   permissions from large Indonesian job boards). The archive's `.id` JobPosting pages
   are dominated by a few dozen regional vacancy blogs; even all past crawls combined
   are unlikely to contain a million distinct vacancies after deduplication.
3. **Required combination:** for 100k: Common Crawl `.id` history (2019–2026) plus Web
   Data Commons' JobPosting subset filtered to Indonesia (non-`.id` domains). For 1M: a
   licensed Indonesia feed (e.g. Techmap per-country files, Lightcast, TheirStack) or
   data-sharing agreements with JobStreet/Glints/Kalibrr/Kemnaker.
4. **Usable immediately and lawfully (with conditions):** Common Crawl archive (research
   analytics; sites with prohibiting or unverified terms excluded); the existing Glints
   academic snapshot (historical, local use). Aggregate open data (Balikpapan) is usable
   but contains counts, not vacancies.
5. **Need permission or licensing:** every live job board (Glints, JobStreet, LinkedIn,
   Indeed, KitaLulus, Karir.com, Kalibrr, Pintarnya), Kemnaker's Pasker ID/Karirhub,
   ATS APIs (per-employer consent), and all commercial job-data providers.
6. **Biggest bottleneck:** permissions. Second: collection rate limits (Common Crawl
   blocked an 8 requests/s run within minutes). Compute and storage are not limiting:
   DuckDB processes 5M synthetic records in seconds on this laptop (BENCHMARKS.md).
7. **Fastest legitimate route to the first 100,000:** buy a licensed Indonesia feed and
   load it with `talentscope lake import-jsonl` (prepared below). Without a budget:
   continue the polite Common Crawl collection over older crawls for several weeks and
   add the Web Data Commons subset once its server is reachable.

## Approaches evaluated

| Approach | Finding | Usable now? |
|---|---|---|
| Official job-board APIs/feeds | None offer bulk read access to third parties; LinkedIn's Job Posting API is inbound-only and closed | No |
| Licensed bulk datasets | Exist (Techmap, Lightcast, TheirStack, Coresignal, LinkUp); paid | Needs budget |
| Official open datasets | Satu Data / regional portals publish **aggregate counts** (e.g. Balikpapan vacancies by education), not listings | Aggregates only |
| Permitted collection from individual sources | Every Indonesian board reviewed prohibits automated collection or requires written permission | No |
| Employer career pages / ATS endpoints | Public ATS APIs exist (Lever, Greenhouse, Ashby) but are intended for the employer's own site; per-employer consent needed | After consent |
| Historical archives | **Common Crawl**: licensed use of the archive; content still subject to site terms → used with site exclusions. **Web Data Commons**: pre-extracted JobPosting subset of the same archive; server unreachable 2026-10-17 | CC: yes (conditions); WDC: blocked (availability) |
| Existing vacancy datasets with provenance | Kaggle/Hugging Face Indonesian job datasets have no licence and appear scraped from boards that prohibit it | No |

## Source-by-source feasibility

Volume labels: **C** = confirmed by our own collection, **E** = estimate from a measured
sample, **V** = vendor claim (unverified), **?** = unknown.

| Source | Access path | Status | Real ID vacancies | Volume | IDs / URLs | Descriptions / salary / dates | Requirement |
|---|---|---|---|---|---|---|---|
| Glints academic snapshot (2026-06) | Existing CSV | Approved w/ conditions | Yes (historical) | **C** 1,133 | No / no | No / 76% / relative only | Local use; confirm republication rights before public use |
| Common Crawl `.id` JobPosting pages | Columnar index + range requests | Approved w/ conditions | Yes (archived) | **C** see DATA_INVENTORY.md; **E** ≈14,500 JobPosting pages in the newest crawl (21% of 68,107 candidates) | Page URL / yes | Yes / ~85% disclosed but often template / yes | Polite rate (≤2 req/s); site exclusions; no description republication |
| Web Data Commons JobPosting subset | Bulk N-Quads download | Blocked (server unreachable) | Yes (archived, all TLDs) | ? (JobPosting found on ~63K websites globally in 2024) | Page URL / yes | Yes | Server availability; same site exclusions |
| Glints (live), JobStreet, LinkedIn, Indeed, KitaLulus, Karir.com, Pasker ID | — | Blocked by terms | Yes | ? (largest volumes in Indonesia) | Yes | Yes | Written permission / data partnership |
| Kalibrr, Pintarnya, Karirhub, Pasker ID datasets | — | Needs written permission | Yes | ? | Yes | Varies | Written permission |
| Dealls, Loker.id, TopKarir, HiredToday, Tech in Asia, SSCASN | — | Needs review | Yes | ? | Yes | Varies | Terms review, then permission |
| foundit.id, jobs.id, profesea.id (found in archive) | — | Excluded (terms not reviewed) | Yes | **E** ≈1,400–1,750 job-like pages each in one crawl | Yes | Yes | Terms review |
| ATS APIs (Lever, Greenhouse, Ashby, SmartRecruiters) | Public JSON APIs | Per-employer consent | Yes (employer-direct) | ? (low thousands; few Indonesian employers confirmed) | Yes / yes | Yes / sometimes / yes | Written consent per employer; connector for Lever ready |
| Techmap / jobdatafeeds | AWS Data Exchange, per-country daily files | Licence | Yes | **V** ASEAN feed ≈527k new postings/month across 10 countries (Jan 2025 listing); Indonesia share unknown | Yes | Yes | Purchase |
| Lightcast | Enterprise licence | Licence | Yes | **V** Indonesia postings since Aug 2020 | Yes | Yes (normalized skills) | Enterprise contract |
| TheirStack | Paid API | Licence | Yes | **V** 195 countries, ≈316k new postings/day globally; Indonesia share unknown | Yes | Yes | Subscription; check redistribution terms |
| Careerjet / Jooble / Adzuna APIs | Publisher (display) APIs | Not suitable | Partly | ? (Indonesia coverage not confirmed) | Yes | Snippets | Designed for live display to visitors, not bulk storage |
| Balikpapan / Satu Data open data | CSV download | Approved w/ conditions (Balikpapan) | Aggregates only | — | — | — | Separate aggregate model |

Source estimates are not additive: the archive and licensed feeds overlap with the
boards they index, and regional blogs repost the same vacancies (see the deduplication
results in DATA_INVENTORY.md).

## Deduplicated volume estimate for Common Crawl

Measured from this run (details and exact figures in DATA_INVENTORY.md): the share of
each additional crawl's JobPosting pages that are new URLs and new canonical vacancies.
The extrapolation there is labelled as an estimate and states its assumptions.

## Integration path for licensed or permitted bulk data

`talentscope lake import-jsonl --source <registry-id> --file export.jsonl` loads a JSON
Lines file of schema.org-style JobPosting objects (one per line, each with `url` and
`captured_at`) into bronze under its own source. Silver, deduplication across sources,
gold, and publishing then work unchanged. Before importing, register the source with its
licence in the registry (`talentscope sources set-status ... --evidence-url <licence>`):
the import is refused for unapproved sources like every other connector.
