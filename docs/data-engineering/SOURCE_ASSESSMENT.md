# Source assessment and prioritization (2026-10-18)

Evidence: four read-only research passes on 2026-10-18 (policy pages, robots.txt, API
docs, dataset licences; no listing data collected), a fifth refresh pass later on
2026-10-18 (§5), plus the earlier review in docs/RESEARCH_SOURCES.md. Counts are checked
against the app database (`select primary_source_id, count(*) from jobs group by 1`:
6,174 + 1,133 = 7,307 after the 2026-10-18 09:40 WIB republish). §6 maps every row to its registry record. Quotes and URLs for the archive's contributing sites are in
DOMAIN_REVIEW.md. Not legal advice. Volume labels: **C** confirmed by our own data, **V**
vendor or press claim (unverified), **?** no evidence. Permission is never inferred from
silence; robots.txt is never treated as a grant.

**Status codes:** 1 Approved for the intended integration · 2 Available with documented
conditions · 3 Requires written permission or a licence · 4 Blocked by applicable
restrictions · 5 Requires further investigation · 6 Implemented and tested.
These codes are this document's planning view; the binding eligibility value is the
registry's `permission_status` (§6). "6 Implemented" says nothing about rights: neither
row 1 nor row 2 rests on a permission granted by the content owner.

## 1. Answers

- **Most realistic route to 100,000 unique vacancies:** a data agreement, not more
  scrapers. Either (a) Kemnaker's Karirhub/SIAPkerja, the national vacancy reporting
  system (press: 753,500 vacancies Jan–Sep 2025), through a formal data request to Pusat
  Pasar Kerja; or (b) a licensed feed such as Techmap (vendor: 32,191 new Indonesian
  postings in Sep 2026, history from 2020), which requires written permission to display
  individual listings because its licence is internal use only. Either route alone
  exceeds 100k after deduplication; nothing usable without permission does.
- **Usable immediately:** the Common Crawl archive (historical only, research use under
  conditions, per-site review enforced; no contributing site grants reuse explicitly) and
  aggregate open data (Balikpapan public domain, Kaltim ODC-BY, BPS with attribution),
  which hold counts, not vacancies. The existing Glints snapshot (historical) is already
  in the app at the project owner's instruction, but its right to be republished is
  **unresolved** (row 2); it has not been cleared for public display.
- **Need external permission:** every live portal (JobStreet, Karir.com, Kalibrr, Dealls,
  KitaLulus), Karirhub, ATS boards (per employer), licensed providers, and the
  Careerjet/Jooble publisher APIs (key plus written storage/display terms).
- **Current listings:** only permission-gated sources (portals, Karirhub, ATS boards,
  licensed feeds) provide current vacancies. **Historical only:** Common Crawl, the
  Glints snapshot.
- **Expected unique volume from what is usable now:** 7,307 today; continued Common Crawl
  collection is ESTIMATED at 4,800–7,200 new vacancies per fully collected older crawl
  (derivation not recorded: DATA_INVENTORY.md has no §8 and does not contain these
  figures; treat as unverified), i.e. 13–20 more crawls (70–145 collection hours) for 100k, all
  historical, with yield in older crawls unverified.
- **Broadest geographic and occupational coverage:** Karirhub (national, all sectors,
  mandatory employer reporting); then large portals; the archive is concentrated on a few
  regional blogs (top 10 sites: 99% of archive vacancies).

## 2. Matrix

| # | Source (domain) | Access method | Coverage | Volume | Active status checkable | Fields | History | Permission / licence | Store | Redistribute | Complexity | Contribution to 100k | Overlap risk | Status | Next action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Common Crawl archive, `.id` JobPosting pages | columnar index + WARC range requests | national, skewed to Aceh/Jabar/Jakarta | **C** 6,174 vacancies (3 crawls, partial) | no (archive); 22 contributing sites reviewed 2026-10-18, none addresses automated re-checks (DOMAIN_REVIEW.md), so none is done | title, employer, place, salary, dates, description | published 2022–2026 (2,030 in 2026, 3,534 in 2025); captured Jul–Sep 2026 | CC limited licence; crawled content stays under each site's terms; 21 of 22 contributing sites silent, 1 permits with backlink (DOMAIN_REVIEW.md) | yes (structured fields; descriptions only in local lake) | not settled: no site grants republication; app shows structured fields + link back, no descriptions | done | 4.8–7.2k/crawl **E**, historical | high with portals it copies | **6** | resume `lake collect` when the owner approves a run |
| 2 | Glints snapshot 2026-06 | one CSV | keyword-sampled, Java-heavy | **C** 1,133 (no per-listing URL) | no | title, employer, city, salary, tags | ≤ 2026-06-13 | registry APPROVED_WITH_CONDITIONS by owner instruction, **not** by Glints; collected by the academic Selenium scraper of glints.com (`legacy/academic_pipeline/scrapers/glints_scraper.py`), while Glints' terms as recorded in SRS §4.1 forbid scraping without written consent | owner decision | **unresolved**: needs Glints' confirmation before any public deployment | done | none further | low | **6** (rights unresolved) | ask Glints, or limit the public site to aggregates |
| 3 | JobStreet (id.jobstreet.com, SEEK) | none for reading; SEEK API is for posting/apply/ad performance | national | ? (largest portal) | n/a | — | — | terms 7(b),(d), 9(b): no aggregation, scraping, bots without written consent | no | no | low once licensed | large | high | **3** | written request via SEEK integration form; no programme for third-party reading exists |
| 4 | Karir.com (PT Qerja Manfaat Bangsa) | none documented | national | ? ("500+ perusahaan", V) | n/a | — | — | §9.2 bans "pengambilan data otomatis tanpa izin"; §8.5 copying/distribution needs prior written permission | no | no | low once permitted | medium | high | **3** | written request (cs@karir.com) stating non-commercial research, fields, retention, rate |
| 5 | Glints (live) | none found | national | ? | n/a | — | — | terms unreadable (HTTP 403 again in the §5 refresh, both `/id/about/terms` and `/id/en/about/terms`); BLOCKED rests on the clause recorded in SRS §4.1 | no | no | — | large | high | **4** | keep blocked; read terms in a browser; request permission |
| 6 | Kalibrr | none | national | ? | n/a | — | — | scraping monitored; written permission required | no | no | — | medium | high | **3** | written request |
| 7 | Dealls (PT SejutaCita) | none | national, tech/young | ? | n/a | — | — | terms found govern the HRIS products; §9.6(2) bars sharing content without written approval; scope over the job board unclear | no | no | — | small | medium | **5** (permission path: 3) | ask which terms govern the job board; written request |
| 8 | KitaLulus | none | national, blue-collar | ? | n/a | — | — | §c.5.18 bans "scraping content"; written permission | no | no | — | medium | high | **3** | written request |
| 9 | Pintarnya | none found | national, SD–S1 | ? ("+100K", V, unlabelled) | n/a | — | — | terms at pintarnya.com/landing/termsandconditions/ (since Nov 2023), re-read in §5: H.2 bars reproducing, copying, distributing or commercial use "tanpa izin tertulis dari Pintarnya"; no scraping clause | no | no | — | ? | ? | **3** | written request |
| 10 | TopKarir | — | ? | ? | — | — | — | site refused connection (2026-10-17 and again in §5, www and bare domain) | ? | ? | — | ? | ? | **5** | treat as unavailable; re-check later |
| 11 | HiredToday (PT Indo HR) | none public | national | ? | n/a | — | — | terms page still client-rendered in §5 (template placeholders only); has an MoU with Kemnaker for Karirhub data integration (to 2028) | ? | ? | — | ? | high with Karirhub | **5** | read terms; ask about research access |
| 12 | LinkedIn | none for third parties | national | ? | n/a | — | — | §8.2 bans scraping/bots | no | no | — | — | — | **4** | none |
| 13 | Indeed Indonesia | no read API found; publisher API retirement reported only by secondary sources | national | ? | — | — | — | terms s.21 (read first-hand 2026-10-17, RESEARCH_SOURCES.md §3.4) ban bots/scrapers without written permission; Indeed's own docs on the publisher API not readable (§5) | no | no | — | — | — | **4** | none; the retirement claim stays unverified |
| 14 | Loker.id | — | ? | ? | — | — | — | homepage HTTP 403 | ? | ? | — | ? | ? | **5** | browser check |
| 15 | Careerjet publisher API (careerjet.co.id) | API with publisher key | aggregated | ? | per query (live search) | snippets | none | key required; storage/display terms not found | unverified | widget display only | low | low (display API, max 1,000 per query) | high | **3** | apply for key; get storage terms in writing |
| 16 | Jooble publisher API (id.jooble.org) | API key on request | aggregated | ? | live search | snippets | none | site §4(i),(m) ban bots and copying; API storage terms unpublished | unverified | "in your own design" | low | low | high | **3** | apply; written storage terms |
| 17 | Karirhub / SIAPkerja (Kemnaker) | web UI only; no API/open data | **national, all sectors** | **V** 753,500 vacancies Jan–Sep 2025 (press) | yes, at source | full vacancy | ongoing | no terms on Karirhub; Pasker terms ban copying and crawlers | no | no | medium (format unknown) | **largest**: alone exceeds 100k | aggregates many portals | **3** | formal data request to Pusat Pasar Kerja (paskerid.kemnaker.go.id) |
| 18 | Pasker ID datasets | CSV/XLSX download | 38 provinces | ~10 aggregate tables, 2022–2024 | n/a | counts | 2022–2024 | no dataset licence; site ToU: personal, non-commercial; no republishing | not without counsel/permission | no | low | **0** (not vacancies) | — | **3** | written confirmation of reuse terms |
| 19 | SSCASN / BKN formasi | search UI | national | ? | per cycle | formation counts | per cycle | not found; site timed out | ? | ? | — | 0 (formations) | — | **5** | re-check |
| 20 | Rekrutmen Bersama BUMN | portal | national | ? | per cycle | vacancies during cycles | — | page did not render | ? | ? | — | small | low | **5** | browser check |
| 21 | Balikpapan open data (Disnaker) | CKAN download/API | Kota Balikpapan | 5 aggregate tables | n/a | counts by education/sex | 2021–2023 | "Other (Public Domain)" | yes | yes | low | 0 (aggregate) | — | **1** (aggregate context) | optional context panel |
| 22 | Kaltim Disnakertrans indicators | CSV | Kalimantan Timur | indicator table | n/a | counts | 2022–2024 | ODC-BY | yes, attribution | yes, attribution | low | 0 | — | **1** (aggregate) | optional |
| 23 | BPS labour statistics | download / API | national | many tables | n/a | aggregates | long | ToU §13 (read first-hand in §5): free, worldwide, non-exclusive, commercial and non-commercial use; credit to BPS with title, access date and link | yes | yes, credit | low | 0 | — | **1** (aggregate) | benchmark denominators |
| 24 | data.go.id & regional portals | catalogue / CKAN | regional | 346 "lowongan kerja" hits, all regional aggregates seen | n/a | counts | varies | licence missing on reviewed pages; Sumsel "not specified" | not by silence | no | — | 0 | — | **5** | dataset-by-dataset licence check |
| 25 | Greenhouse / Lever / Ashby boards | public JSON APIs | ~20 Indonesian employers found (GoTo, Xendit, DKatalis, Amar Bank, aCommerce, …) | **V** a few hundred openings in total | **yes** (board lists only open jobs) | full | current only | docs frame APIs for the employer's own careers site; silent on third parties (Lever: "may be scraped by third parties" is not a licence) | no without consent | no without consent | low | small (< 1k) | low | **3** | per-employer written consent; Lever connector already built |
| 26 | SmartRecruiters / Workday / Mekari Talenta | key / no public API | Siloam (~450), Cermati (~236), CTBC, Akulaku … | **V** | yes at source | full | current | credential or none | no | no | medium | small | low | **3** | employer consent |
| 27 | Employer career pages (banks, telco, SOEs, retail) | own portals | national | ? | yes at source | varies | current | site terms not reviewed; no reuse grant found | no | no | high (many formats) | medium, fragile | medium | **3** | consent per employer; prefer partnerships |
| 28 | Techmap (jobdatafeeds.com, AWS Data Exchange) | licensed files/API | Indonesia listed | **V** 32,191 new postings Sep 2026; 27 sources; from 2020 | feed has 3-month rolling window | full | 2020– | AWS: "internal use; may not be resold"; display needs written permission | yes (licensed) | not without permission | low (JSONL import ready) | **large** (100k in ~3–4 months of feed or from history) | high with portals | **3** | ask legal@techmap.io for display rights; budget decision |
| 29 | Lightcast | enterprise licence | Indonesia since Aug 2020 | ? | real-time per vendor | normalized skills | 2020– | contract | contract | unknown | low | large | high | **3** | sales contact |
| 30 | TheirStack / Coresignal / LinkUp / Revelio | APIs / datasets | global; Indonesia unconfirmed | ? | varies | varies | 2007–/2021– | terms not published or contract | ? | ? | low | ? | high | **5** | confirm Indonesian volume and display terms |
| 31 | Bright Data job datasets | datasets | global | ? | — | — | — | partly LinkedIn/Indeed-derived | — | — | — | — | — | **4** | avoid (derived from prohibiting sources) |
| 32 | Proxycurl | — | — | — | — | — | — | shut down after LinkedIn injunction (2025) | — | — | — | — | — | **4** | none |
| 33 | Web Data Commons JobPosting subset | bulk N-Quads | global incl. non-`.id` Indonesian sites | ? | no (archive) | structured | 2013– | CC-derived; same per-site review needed | yes | as row 1 | medium | medium **E** | high with row 1 | **5** | server unreachable 2026-10-17 and again in §5 (connection refused); re-check |

## 3. Volume ledger (no addition across overlapping sources)

| Bucket | Records | Notes |
|---|---:|---|
| Confirmed, validated, in the app | **7,307** | 6,174 archive (22 publisher sites) + 1,133 snapshot; 0 cross-source matches (DB query, 2026-10-18) |
| Accessible but unprocessed | ≈ 0.6–0.7M archive candidate pages in the 9 untouched crawls of the 12 discovered/discoverable; JobPosting yield ≈ 21% | only Common Crawl; historical |
| Estimated potential (usable now) | 4.8–7.2k new vacancies per older crawl **E** | derivation not recorded (DATA_INVENTORY.md has no §8); unverified |
| Requires licence/agreement | Karirhub ≈ 0.75M/yr **V**; Techmap ≈ 32k/month **V**; portals ? | overlap between them is high (Karirhub aggregates portals) |
| Unusable under current restrictions | JobStreet, Karir.com, Kalibrr, KitaLulus, Dealls, LinkedIn, Indeed, Pintarnya, Glints live content; groove.co.id plus 9 other archive sites (2 quality, 6 unreadable, 1 unreviewed) | see matrix and DOMAIN_REVIEW.md |

## 4. Connectors implemented and tested now

- **Common Crawl archive** (row 1): implemented earlier; this round added enforced
  per-site review (default deny) and the campaign/placeholder corrections; tests and a
  real rebuild/publish run (DATA_INVENTORY.md).
- **JSON Lines import** for a licensed feed: implemented and tested with fixtures; no
  licensed data exists to run it on.
- **No new vacancy connector was implemented**, because no candidate source has an
  approved access path for collection, storage, and display. Building scrapers for
  sources that require permission would violate their terms. The aggregate open-data
  sources (rows 21–23) are approved but contain counts, not vacancies, so they cannot
  contribute to the vacancy target.

## 5. Refresh of unresolved items (2026-10-18, later pass)

Read-only WebFetch of policy, API-doc and availability pages only; no listing pages.
Quotes are as returned by the fetch tool; re-check in a browser before relying on them.

| Item | URL | Result on 2026-10-18 | Effect |
|---|---|---|---|
| Glints terms | https://glints.com/id/about/terms, https://glints.com/id/en/about/terms | **unreadable** (HTTP 403 on both). robots.txt readable: one `*` group disallowing explore/recommended/bookmarked pages, account pages, `/api/gt/` and tracking endpoints | BLOCKED still rests on the SRS §4.1 record; the clause was not re-verified |
| Pintarnya terms | https://pintarnya.com/landing/termsandconditions/ | readable. "berlaku sejak tanggal November 2023"; H.2: "Tidak diperkenankan mereproduksi, memodifikasi, menyalin atau mendistribusikan atau menggunakan untuk tujuan komersial … tanpa izin tertulis dari Pintarnya"; no scraping/bot clause | row 9 → 3, matching the registry (REQUIRES_WRITTEN_PERMISSION); the earlier "terms URL not found" was wrong |
| TopKarir availability | https://www.topkarir.com/, https://topkarir.com/ | **unreachable** (connection refused, ECONNREFUSED) | still 5 |
| HiredToday terms | https://www.hiredtoday.com/en/term | **unreadable**: client-rendered, only `{{"footer.term_of_use" \| translate}}` placeholders | still 5 |
| Indeed publisher API (Indeed's own docs) | https://docs.indeed.com/, https://developer.indeed.com/ → 301 → https://partners.indeed.com/ | docs root and partners site **HTTP 403**. https://docs.indeed.com/job-sync-api readable: "a GraphQL API for ATS partners to create, upsert, expire, and check the status of job postings on Indeed"; no mention of a publisher/search API | retirement of the publisher API remains **unverified** first-hand; irrelevant to eligibility because s.21 of the terms already blocks collection |
| Web Data Commons | https://webdatacommons.org/, https://webdatacommons.org/structureddata/ | **unreachable** (connection refused) | still 5 |
| Common Crawl terms (re-read for the public condition text) | https://commoncrawl.org/terms-of-use | §1 "limited, non-assignable, non-transferable, non-sublicensable, non-exclusive" licence; §2 crawled content "may be subject to separate terms of use or terms of service from the owners"; §3 recommends legal counsel "before making any use, including commercial use" | confirms row 1: the archive licence does not grant rights in the sites' content |
| BPS terms | https://www.bps.go.id/id/term-of-use | readable (was HTTP 403 on 2026-10-17). §13: "secara gratis, di seluruh dunia, terus-menerus, dan non-eksklusif", for "kepentingan komersial maupun nonkomersial"; condition "memberikan kutipan atau kredit kepada BPS" with title, access date and direct link | registry entry `bps-statistics` (NEEDS_REVIEW) is stale; see §6 |

## 6. Traceability to the source registry

Registry read-only on 2026-10-18 (`select id, name, permission_status, technical_method,
reviewed_at from sources order by id;` → 29 rows: the 2 code-defined entries in
`backend/talentscope/sources.py` plus the 27 entries of `docs/research/source_matrix.json`).

| Row | Registry id | Registry status | Agrees with this document? |
|---|---|---|---|
| 1 | `commoncrawl-jobposting` | APPROVED_WITH_CONDITIONS | yes; per-site decisions are in `lake/domain_reviews.py` (32 domains) |
| 2 | `glints-snapshot-2026-06` | APPROVED_WITH_CONDITIONS | status yes; the public label overstates it (DATA_POLICY.md "Public labels") |
| 3 | `jobstreet` | BLOCKED | yes (3 here = permission path; collection blocked) |
| 4 | `karir-com` | BLOCKED | yes (as row 3) |
| 5 | `glints` | BLOCKED | yes |
| 6 | `kalibrr` | REQUIRES_WRITTEN_PERMISSION | yes |
| 7 | `dealls` | NEEDS_REVIEW | yes after this correction (was 3) |
| 8 | `kitalulus` | BLOCKED | yes |
| 9 | `pintarnya` | REQUIRES_WRITTEN_PERMISSION | yes after this correction (was 5) |
| 10 | `topkarir` | NEEDS_REVIEW | yes |
| 11 | `hiredtoday` | NEEDS_REVIEW | yes |
| 12 | `linkedin-jobs` | BLOCKED | yes |
| 13 | `indeed-indonesia` | BLOCKED | yes after this correction (was "5, likely 4") |
| 14 | `loker-id` | NEEDS_REVIEW | yes |
| 15, 16 | none | — | **no registry record** (Careerjet, Jooble) |
| 17 | `karirhub-kemnaker` (+ `pasker-id`, BLOCKED, for the HTML site) | REQUIRES_WRITTEN_PERMISSION | yes |
| 18 | `pasker-id-datasets` | REQUIRES_WRITTEN_PERMISSION | yes after this correction (was 2) |
| 19 | `sscasn-bkn` | NEEDS_REVIEW | yes |
| 20 | none | — | **no registry record** (Rekrutmen Bersama BUMN) |
| 21 | `balikpapan-opendata-vacancies` | APPROVED_WITH_CONDITIONS | yes (aggregate only) |
| 22 | none | — | **no registry record** (Kaltim Disnakertrans, ODC-BY) |
| 23 | `bps-statistics` | NEEDS_REVIEW | **no**: terms now read (§5); registry should be re-reviewed |
| 24 | `satu-data-indonesia` | NEEDS_REVIEW | yes |
| 25 | `greenhouse-job-board-api`, `lever-postings-api`, `ashby-posting-api` | REQUIRES_WRITTEN_PERMISSION | yes |
| 26 | `smartrecruiters-posting-api`, `workday-career-sites` | REQUIRES_WRITTEN_PERMISSION | yes; Mekari Talenta has no record |
| 27 | none | — | **no registry record** (employer career pages; per-employer, by design) |
| 28–33 | none | — | **no registry record** (Techmap, Lightcast, TheirStack/Coresignal/LinkUp/Revelio, Bright Data, Proxycurl, Web Data Commons) |
| — | `tech-in-asia-jobs`, `schema-org-jobposting`, `kaggle-indonesia-job-datasets` | NEEDS_REVIEW | in the registry, absent from this matrix (none is a candidate: Tech in Asia unreadable, schema.org is a technique, Kaggle sets are derived from portals that ban aggregation) |

Rows without a registry record are research notes only. A source cannot run without a
registry record (`ingestion/policy.py`), so none of them can be activated by accident;
before any of them is pursued, a registry entry with evidence must be added.
