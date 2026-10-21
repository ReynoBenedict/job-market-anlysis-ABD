# Data lake: collection, processing, and analytics pipeline

Design rationale: [ADR-0015](adr/0015-data-lake.md). Source permissions: [DATA_POLICY.md](DATA_POLICY.md).
All commands run from the repository root with `DATABASE_URL` set; the lake lives in
`LAKE_DIR` (default `./lake`, git-ignored).

```
Common Crawl columnar index (remote Parquet)            Common Crawl WARC files (remote)
        │  lake discover: .id pages with job-like URLs,          ▲
        │  minus excluded sites                                  │ one HTTP range request per page
        ▼                                                        │ (stops on 403/429)
bronze/commoncrawl/candidates/crawl=*/candidates.parquet ── lake collect ──┘
bronze/commoncrawl/captures/crawl=*/batch-*.parquet      JobPosting JSON + provenance, append-only
bronze/commoncrawl/reobservations/crawl=*/*.parquet      unchanged re-captures (index only)
        │  lake silver (incremental)
        ▼
silver/observations/*.parquet   one per bronze file (parsed, validated, skills extracted)
silver/observations_all.parquet captures + re-observations
silver/source_records.parquet   one per page posting; first/last seen; salary reliability
silver/vacancies.parquet        canonical vacancies after deduplication
        │  lake gold
        ▼
gold/*.parquet  + gold/report.json (inventory, completeness, coverage, quality)
        │  lake publish
        ▼
PostgreSQL jobs (app/API) — one job per canonical vacancy, no descriptions
```

## Commands

| Command | What it does | Re-run safe? |
|---|---|---|
| `talentscope sources sync` | registers the Common Crawl source (policy gate) | yes |
| `talentscope lake discover --newest N` / `--crawl ID` | writes candidates per crawl (skips existing unless `--force`) | yes |
| `talentscope lake collect --newest N [--max-pages K] [--workers 2] [--rps 1]` | fetches pending candidates; resumes where it stopped | yes |
| `talentscope lake silver [--full]` | parses new bronze files, rebuilds records and vacancies | yes |
| `talentscope lake gold` | rebuilds analytics tables and report.json | yes |
| `talentscope lake publish` | loads vacancies into the app DB (policy-gated, idempotent) | yes |
| `talentscope lake run [--publish]` | silver → gold (→ publish) | yes |
| `talentscope lake report` | prints the inventory from report.json | yes |
| `talentscope lake benchmark --sizes ...` | DuckDB vs Spark on SYNTHETIC data (`pip install -e "backend[bench]"`) | yes |

## Collection behaviour
- **Policy gate:** discover and collect refuse to run unless the registry entry
  `commoncrawl-jobposting` is approved and reviewed within 365 days.
- **Rate limits:** default 2 workers, 2 requests/s (the overnight run used 1 request/s).
  HTTP 403 (CloudFront rate-limit rule) or persistent 429 raises `AccessBlocked`: the run
  stops, queued work sends no further requests, the partial batch is kept, and the run is
  recorded as `ACCESS_DENIED`. 5xx and network errors are retried with exponential
  backoff (2 s → 60 s), then recorded as transient failures and retried on the next run.
- **Resumability:** a record already fetched successfully (or permanently failed) is never
  fetched again; transient failures are retried.
- **No needless downloads:** a URL whose content digest matches an earlier capture is
  recorded as a re-observation from the index alone; a domain with no JobPosting markup
  after 15 pages is skipped; domains with proven yield are fetched first.
- **Retention:** bronze keeps the JobPosting objects only, never page HTML.

## Counting levels (never mixed in reports)
1. **Archived pages fetched** / **pages with JobPosting**.
2. **Observations:** every JobPosting in every capture, plus unchanged re-captures.
3. **Source records:** one per page posting (URL + position on the page). Site
   identifiers are recorded but not trusted as keys (template values such as `"1"` occur).
4. **Canonical vacancies:** after deduplication (below).
5. **Freshness:** no vacancy is described as currently open. A *reliable* `valid_through`
   (see "Deadline reliability") before the last capture marks it expired at that capture;
   otherwise its status is unknown. In the app a deadline means "open through that day in
   Indonesia": it is published as 23:59:59 WIB of the date, so a job is not shown as expired
   on its deadline day.

## Validation (silver)
**Site review (default deny):** archived pages are used only from sites with a usable
per-site review (`lake/domain_reviews.py`, docs/data-engineering/DOMAIN_REVIEW.md);
other sites stay in bronze and are counted in `report.json → domain_governance`.

Invalid (excluded from vacancies): missing title, missing hiring organization, a
placeholder employer (a filler word such as "Perusahaan"/"Company", or the site's own
name, optionally with job-board words: "Lokermu" on lokermu.id, "Lorong Jobs" on
lorong.my.id). Not placeholders: a withheld employer ("Rahasia", "Dirahasiakan" → shown as
"Perusahaan dirahasiakan") and a household employer ("ART (Pembantu Rumah Tangga)" →
"Perorangan (rumah tangga)") are real vacancies, kept with a flag. Also invalid: titles of non-vacancy articles
(tips, CV examples, selection results...), explicit non-Indonesian country.

**Titles:** HTML entities are decoded. The displayed `title` drops blog boilerplate
("Lowongan Kerja …", "(Lamar Sekarang)", "- Bisa Kerja", "Terbaru 2026") and an employer
name repeated twice; the original is kept as `source_title` and shown on the job page. Flags (kept, reported): province unresolved, multi-location, posting date
missing/unparseable/implausible (future or before 2010), validThrough before
datePosted, expired at capture, description missing/thin, salary currency/period
missing, single-value, wide-range, and low/high outlier salaries.

**Salary reliability** (`salary_reliable`, with the reason in `salary_unreliable_reason`):
- `SITE_TEMPLATE`: a site whose disclosed salaries are ≥50% one identical range (≥10
  records) is using a theme default; none of its salaries are used.
- `BELOW_MONTHLY_FLOOR`: a monthly IDR midpoint below Rp500,000 (`IDR_MONTHLY_LOW_OUTLIER`,
  the same floor the API's salary statistics use) is not a plausible monthly wage
  (seen: "Rp2 – Rp897 per bulan" on lokerbekasi.my.id, 3 vacancies).
- A range with minimum > maximum is already `INVALID` at parsing and never has monthly values.

Unreliable salaries are kept in silver but never enter gold statistics, and `lake publish`
sends them as an explanatory text without any amount (never as zero). Hourly/daily/weekly
pay and non-IDR currencies are never converted into monthly IDR statistics. Monthly
maxima above Rp100 million are flagged (`SALARY_HIGH_OUTLIER`) but not removed.

**Deadline reliability** (`valid_through_reliable`, `deadline_template_site`): some site
themes fill validThrough with a default instead of the employer's deadline. A site with
≥20 deadlines is a deadline-template site when ≥25% of them are **one identical date** or
**one identical number of days after datePosted**; none of its deadlines are then used as
application deadlines (the source value stays in silver and in the app's `raw_fields`).
Measured 2026-10-18 on usable sites (source records):

| Site | Deadlines | Most common date | Most common offset | Decision |
|---|---:|---|---|---|
| bisakerja.id | 362 | 2026-08-23 on 100% (pages posted 2023–2024) | +774 days, 6% | template |
| mediaanalisindonesia.co.id | 125 | 2026-07-17 on 100% | +77 / +60 days, 4% each | template |
| lokerbekasi.my.id | 438 | 4% | +60 days on 29% (+29 on 22%) | template |
| lokerbandung.or.id | 25 | 20% | 12% | kept |
| lokerbogor.co.id | 185 | 14% | +30 days, 17% | kept |
| every other site with ≥20 deadlines | — | ≤ 13% | ≤ 12% | kept |

Not detectable by this rule: sportsmatters.id gives every page a deadline 31–61 days
after posting, spread evenly, and never states a date in the text. That pattern is
suspicious, but a "narrow band" rule would also flag genuine sites (lokeraceh.id has 98%
of its deadlines inside one 31-day band, because most real deadlines are 3–4 weeks out),
so those deadlines are kept and shown as the source's.

## Deduplication (silver → vacancies)
1. **Exact:** same employer key, normalized title key (blog boilerplate, employer name,
   and the posting's own place names, including street/district and region, removed),
   and place (city, else province). Records
   are split into separate openings when consecutive posting dates (or first-seen dates)
   are more than 45 days apart, so a role re-advertised months later is a new vacancy.
   This merges reposts on one site and the same vacancy syndicated across sites.
2. **Fuzzy:** inside an employer + place block, title keys with Jaro-Winkler ≥ 0.93
   and anchor dates within 45 days are merged (union-find).
3. **City-templated campaigns:** when one site posts the same employer + role for ≥5
   places **and at least 80% of those pages show one identical salary (or none)**, they
   are copies (SEO pages per city or subdistrict, e.g. bisakerja.id's "Info Loker
   Indomaret <kecamatan>"): one vacancy with no single place, excluded from city/province
   counts, shown as "Banyak lokasi". When salaries differ by place (regional pay), the
   pages are genuine local openings and stay separate vacancies. Measured on real data
   before this condition: sites like sportsmatters.id had 4–12 distinct salaries per group,
   bisakerja.id exactly one. **A campaign is one vacancy for its whole observed life: the
   45-day window does not split it**, because a campaign's page dates record when the
   site generated pages, not hiring rounds (bisakerja.id generated the same "ART
   (Pembantu Rumah Tangga) <kecamatan>" pages in batches dated 2023-10, 2023-12, 2024-04
   and 2024-07). Rotating SEO words ("Terkini", "Terupdate") are ignored in title keys.
   Before this change 6 of 26 campaigns were split into 16 vacancies; now there are 24
   campaigns, one vacancy each (−12 vacancies, all on bisakerja.id).
4. Genuinely different places from different sites stay separate vacancies.

**Counting semantics** (what one canonical vacancy is):

| Situation | Counted as |
|---|---|
| The same page captured again (same or another crawl) | one more *observation*, same vacancy |
| A repost on the same site, or the same vacancy on another site, within 45 days of the previous record | the same vacancy (*repost* / *syndication*) |
| The same employer + role + place re-advertised after a gap of more than 45 days | a new vacancy (a new hiring round) |
| The same employer + role in another place (different pay, or fewer than 5 places) | one vacancy per place (*location-specific openings*) |
| Copies of one page for ≥5 places with one salary (SEO campaign) | one vacancy without a single place, regardless of dates (*campaign*) |

Known limitation: a campaign whose site rotates the employer's name ("Indomaret",
"Indomaret Group", "PT Indomarco Prismatama" on bisakerja.id) or puts the role into the
employer field ("Kurir Motor JNE" / "Kurir Motor JNE Express") forms one campaign per
spelling, because employer names are not mapped to a canonical employer.

**Place names:** a regency is written one way ("Kab. Bandung", "KAB Bandung" →
"Kabupaten Bandung") in silver and in the app, so the Glints snapshot and archive sites
do not count one regency as two cities. "Kota X" and bare names stay as written ("Bogor"
can be the city or the regency).

## Publishing
`lake publish` loads one app job per canonical vacancy, keyed by `vacancy_id` (a hash
of the vacancy's smallest member record key). A rebuild can change that key: a vacancy
merged into another, a record newly marked invalid, or a site newly excluded. So the run
also **retires** this source's app records whose key is not in the current silver build,
and deletes jobs left with no source record (jobs also backed by another source are
kept). Each retirement is written to `audit_events` (`source.records_retired`).

**All or nothing.** The publish is a complete snapshot (`Connector.replaces_snapshot`):
upserts and retirements happen in **one transaction**. If the connector fails, a record is
rejected, or a record limit stops the run, everything is rolled back, the previous
snapshot stays as it was, and only the run row remains (status `FAILED`,
`details.rolled_back = true`, message "... nothing was published"). Before 2026-10-18 the
pipeline committed every 250 records and retired only after success, so a failure midway
left part of a new build mixed with the old one, presented as if complete.

**What publish sends for unreliable values** (contract with the API and frontend):
- unreliable salary: no amount; `salary_text` is "Nilai gaji berasal dari templat situs
  dan tidak dipakai" (site template) or "Nilai gaji di situs asal tidak wajar (di bawah
  batas minimum gaji bulanan) dan tidak dipakai" (below the floor); the app stores them as
  `UNPARSEABLE`;
- deadline from a deadline-template site: `expires_at` is empty, and
  `source_records.raw_fields` carries `source_valid_through` (the site's date, ISO) and
  `valid_through_unreliable: true`. Every archive record carries both keys
  (`valid_through_unreliable: false` when the deadline is used);
- a used deadline is `expires_at` = 23:59:59 WIB on that date.

## Incident log
- **2026-10-17 15:41 WIB:** the first collection run at 8 requests/s (8 workers) received
  HTTP 403 from Common Crawl's CloudFront rate-limit rules after ≈2,800 requests. The
  collector at that time treated 403 as a per-record failure; 847 requests failed before
  it was stopped manually. Fixes: stop-on-403/429 with no further requests, retry of
  transient failures, lower default rates. Access was available again at 15:45.

## Recovery
- Interrupted collection: re-run the same command.
- Changed parsing rules: bump `PARSER_VERSION` (postings.py) or
  `SKILL_DICTIONARY_VERSION` (skills.py); `lake silver` then reparses everything.
- Corrupt silver/gold: delete `lake/silver` and `lake/gold` (and
  `lake/state/silver_manifest.json`), run `lake run`. Bronze is the source of truth.
- Site owner opt-out: add the domain to `EXCLUDED_DOMAINS` (discovery skips it and the
  next `lake silver` drops it from silver and gold), delete its bronze files if retention
  requires, then run `lake run --publish`: publishing retires app records that silver no
  longer contains (below).
