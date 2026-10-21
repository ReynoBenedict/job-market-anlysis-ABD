# End-to-end quality audit (2026-10-18)

Owner: tech lead. Companion files: [INTERACTION_MATRIX.md](INTERACTION_MATRIX.md)
(every control, verified in a browser), [DATA_CONSISTENCY.md](DATA_CONSISTENCY.md)
(counts reconciled against the database). Severity: **P0** wrong/misleading data or
broken core journey · **P1** significant UX/trust problem · **P2** minor · **P3** polish.

## 1. Baseline (before any change)

| Item | State |
|---|---|
| Branch / commits | `main`, nothing committed in this work; 53 working-tree entries (user's staged renames of the academic files preserved) |
| Background processes | none (Common Crawl collector stopped by the owner on 2026-10-17) |
| Docker | db, api, web healthy; ports 5433 / 8010 / 3001 |
| Database | 7,319 jobs (6,186 archive + 1,133 snapshot), 7,319 source records |
| Raw files | `data/raw/glints_jobs.csv` sha256 `c29229793e7be34149bf1f1965a12143c1d09ba777361d003496adc867e58d95`; `data/` identical to HEAD |
| Recoverable baseline | `pg_dump` of the app DB, tarball of the working tree, diffs of staged/unstaged changes (session scratchpad `baseline/`) |
| Dev servers for the audit | API from the working tree on :8011, Next dev on :3002 |

## 2. Team and file ownership

Five workers plus the tech lead (this session). No two workers edit the same file.

| Worker | Role | Owns |
|---|---|---|
| W1 | Source governance & product research | docs/data-engineering/SOURCE_ASSESSMENT.md, DOMAIN_REVIEW.md, docs/RESEARCH_SOURCES.md, docs/DATA_POLICY.md |
| W2 | UX/UI & accessibility | homepage, sumber-data, metodologi, keterampilan pages; components/ui.tsx, charts/, shell/, data-scope.tsx, globals.css, not-found |
| W3 | Frontend interaction | lowongan/**, gaji, ringkasan, pasar, tersimpan pages; components/explorer/, jobs/; lib/ (not api-schema.ts); proxy.ts; e2e/; playwright config; INTERACTION_MATRIX.md |
| W4 | Backend, API, security | api/, analytics/, models, migrations, config, db, vocab.py, tests/integration (not lake publish), pyproject, docs/API.md |
| W5 | Data engineering & analytics | lake/, ingestion/, normalization/, sources.py, tests/unit, test_lake_publish.py, LAKE.md, DATA_INVENTORY.md, ML_EVALUATION.md, docs/ml/, DATA_CONSISTENCY.md |
| Lead | Integration | this file, lib/api-schema.ts (generated), republishing, container rebuilds, final verification |

## 3. Application surface

**Public routes:** `/` · `/lowongan` (query: q, province, city, role_family,
employment_type, work_arrangement, education, experience, source, freshness,
salary_min, salary_max, salary_disclosed, sort, page) · `/lowongan/[id]` (query:
`kembali`) · `/lowongan/tidak-ditemukan` (404 target) · `/gaji` (filters + `by`) ·
`/ringkasan` · `/pasar` (filters) · `/keterampilan` (`role_family`) · `/tersimpan` ·
`/sumber-data` · `/metodologi` (anchors incl. `#koreksi`) · unknown routes → 404.
**Admin (Basic auth; disabled when credentials are unset):** `/admin`,
`/admin/riwayat`, `/admin/kualitas`, `/admin/audit`.
**API (`/api/v1`):** `GET /health`, `/jobs`, `/jobs/{id}`, `/filters`,
`/market/overview`, `/market/breakdown/{dimension}`, `/salaries/overview`,
`/salaries/compare`, `/skills/source-tags`, `/sources/coverage`; admin: `/admin/sources`,
`POST /admin/sources/{id}/pause|resume`, `/admin/ingestion-runs[/{id}]`,
`/admin/data-quality`, `/admin/audit-events`; docs at `/api/docs`.

## 4. Findings

Confirmed defects, grouped by area. Control-level UI defects (about 20 rows, mostly P2)
are listed one by one in [INTERACTION_MATRIX.md](INTERACTION_MATRIX.md) and only
summarized here. "Verified" means checked on the rebuilt containers (:3001 / :8010) after
the republish, unless stated otherwise.

### 4.1 Data and status (P0/P1)

| # | Sev | Defect | Root cause | Fix (files) | Regression test |
|---|---|---|---|---|---|
| D1 | P0 | 546 archive vacancies were "Kedaluwarsa menurut sumber" because of a deadline that is a site theme default (one date or a fixed offset on every posting) | `validThrough` trusted as the source's deadline | `mark_deadline_templates` in `lake/silver.py` (≥ 20 deadlines, ≥ 25% same date/offset); template deadlines are not published as `expires_at` and are kept as raw `source_valid_through` + `valid_through_unreliable` (`ingestion/connectors/lake_vacancies.py`, parser lake-vacancies/2); job page explains it (`lowongan/[id]/page.tsx`) | `test_lake_pipeline` (template detection), `test_lake_publish` |
| D2 | P0 | A vacancy was shown as expired on its deadline day (deadline stored as 00:00) | date-only deadline converted to midnight | deadlines published as 23:59:59 WIB | `test_lake_publish` (edge case: published 11 Sep, archived 12 Sep, deadline 10 Nov) |
| D3 | P1 | SEO campaigns (one page copied for ≥ 5 places) were split into several vacancies by the 45-day rule (36 campaigns → 24 after the fix) | sessionization applied before campaign grouping | campaign = one vacancy for its whole life; 45-day split only for non-campaigns (`lake/silver.py`) | `test_lake_pipeline` (+campaign cases) |
| D4 | P1 | 3 implausible salaries (Rp 2 – Rp 897 per month) published and shown as amounts; histogram had a "0" bin | no plausibility floor on publish or display | one rule `analytics/salary_rule.py` (DISCLOSED, IDR, monthly bounds, min ≤ max, midpoint ≥ Rp 500,000) used by overview/compare/histogram/filters/sort; `Salary.comparable`; pipeline flags `IMPLAUSIBLE_SALARY_TEXT`; UI shows "Angka gaji di sumber tidak wajar" | `test_api_contracts`, `test_lake_publish`, vitest, E2E D2 (skipped: no such record left in the data) |
| D5 | P1 | "Kab. X" and "Kabupaten X" counted as two cities (573 → 524 values) | no canonical regency prefix | `canonical_city` in `normalization/location.py` (NORMALIZATION_VERSION 1.3) | `test_text_and_location` |
| D6 | P1 | A failed snapshot publish could leave a half-retired dataset | retirement ran outside the run transaction | `Connector.replaces_snapshot`; run + retirement in one transaction, rollback on failure (`ingestion/pipeline.py`, `connectors/base.py`, `lake/commands.py`) | `test_lake_publish` (+4, incl. failure rollback); rerun: created 0 / updated 0 / retired 0 |
| D7 | P2 | Title keys kept "terkini"/"terupdate" (SEO words), splitting duplicates; campaign organization chosen nondeterministically | key normalization; `any_value` | PARSER_VERSION 15; deterministic `min(organization)` (`lake/postings.py`, `lake/gold.py`) | `test_lake_pipeline` |

### 4.2 Source semantics and trust (P0/P1)

| # | Sev | Defect | Fix | Test / evidence |
|---|---|---|---|---|
| S1 | P0 | Both source badges said "Disetujui dengan syarat", which overstated permission. The Glints snapshot was collected by a Selenium scraper with no permission on record; for Common Crawl, the publishing sites are silent on reuse | public labels separate from the internal enum (`sources.public_label`/`public_condition`, migration `0002_source_public_label.py`, `sources.py`, `vocab.py`); "Data historis — hak tayang ulang belum dipastikan" and "Dipakai untuk riset, dengan syarat"; Sumber Data page shows the condition, with the English review reason under "Catatan teknis" | `test_api_contracts`; DB after `sources sync`; screenshot |
| S2 | P1 | "N sumber" was ambiguous (2 datasets vs 22 publisher sites) | `publisher_sites` in `MarketOverview` / `DatasetScope`; homepage "7.307 lowongan tercatat dari 2 kumpulan data dan 22 situs asal" | `test_api_contracts`; E2E A |
| S3 | P1 | `observed_from/to` were described as collection dates; they are archive capture dates | wording in DATA_POLICY, SOURCE_ASSESSMENT §6, UI scope | doc review |
| S4 | P2 | Keterampilan tag links ran a free-text search (`?q=`), so counts did not match the tag | exact `tag` filter (`Job.source_tags.overlap`), `?tag=` links with `role_family`, chip "Tag: …" | `test_tag_filter_matches_exact_card_tags`; E2E H/H2 (result total == tag count) |

### 4.3 Frontend and UX (P1/P2)

| # | Sev | Defect | Fix | Test |
|---|---|---|---|---|
| U1 | P1 | Homepage presented the archive as a job board | pill "Arsip lowongan, bukan yang sedang dibuka"; headline about past vacancies and salaries | E2E A; screenshots at 6 viewports |
| U2 | P1 | Histogram drawn at a fixed width (scaled text, clipped labels at 360 px); first bin read "0" | real-width rendering, edge labels, "di bawah Rp 2 jt" (`charts/histogram.tsx`, `charts/ticks.ts`) | vitest; screenshots |
| U3 | P1 | Unknown job ids returned HTTP 200 with a not-found body | proxy returns the prerendered not-found page with status 404 | E2E C (status 404); outage case stays 200 + error state (local-stack) |
| U4 | P2 | Skip link did not move focus; the mobile menu ignored Escape and did not return focus | `<main id="konten" tabIndex={-1}>`, menu Escape and focus return, `scroll-padding-top` | E2E K; axe |
| U5 | P2 | Results: "0 lowongan" not emphasized, sort shown with no results, retry dropped the search, salary inputs kept stale values, unknown `sort`/huge `page` produced 422 pages, saved job deleted at source had no way out | INTERACTION_MATRIX rows (FIXED) | E2E B, B2, E, E2, I; vitest |
| U6 | P2 | Skills denominators unclear; quartile chart had no explanation | captions naming the denominator; `/gaji` description of p25–p75 and median | review + screenshots |

### 4.4 Backend, API, security (P1/P2)

| # | Sev | Defect | Fix | Test |
|---|---|---|---|---|
| B1 | P1 | NUL bytes or very long filter values produced 500s | validation: NUL or > 200 characters → 422, and `field` names the query parameter | `test_api_contracts` |
| B2 | P2 | Admin `source_id` not validated; `source_url` could be a non-http(s) scheme; `X-Request-ID` echoed unsanitized; health check swallowed every exception | validation, http(s)-only URLs, sanitized request id, health catches DB errors only | `test_api_contracts` |
| B3 | P2 | The /filters salary range and `salary_desc` sort included implausible values | shared salary rule (D4) | `test_api_contracts` |

### 4.5 Regression introduced and reverted during the audit

Binding the Compose ports to `127.0.0.1` (privacy hardening) broke the CLI's database
access on this machine: Windows resolves `localhost` to `::1` first, and Docker Desktop
ignored `[::1]` bindings, so connections hung for 25–130 s. `docker-compose.yml` and
`backend/Dockerfile` were restored byte-identical to the baseline (checked with `cmp`), and
connections take 0.03 s again. This is kept as a recommendation (§6).

## 5. Verification (2026-10-18, after integration and republish)

| Check | Result |
|---|---|
| Backend: ruff, ruff format, mypy (62 files) | clean |
| Backend: pytest (separate test database) | 305 passed |
| Frontend: tsc, eslint, vitest | clean, 26/26 |
| Frontend: `npm run build` | OK |
| E2E on the running app (3001/8010), desktop + mobile, journeys A–K | 33 passed, 1 skipped (D2: no implausible salary left to show) |
| E2E local-stack (admin, outage and recovery, 404 vs outage) | 6/6 passed |
| axe (11 pages) | 0 violations |
| Viewports 1440×900, 1280×720, 1024×768, 768×1024, 390×844, 360×800 | screenshots inspected; no horizontal scroll (E2E viewport journey) |
| Republish idempotency | second run: created 0, updated 0, retired 0 |
| Raw CSV | sha256 unchanged |

## 6. Open items (not fixed, decision or resource needed)

| Item | Sev | Why open |
|---|---|---|
| Glints snapshot republication right | P0 for any public deployment | No permission on record (scraper-collected). The owner must decide whether to obtain consent or remove the data before going public. Labelled honestly in the app meanwhile |
| Employer alias table | P2 | Same employer under different spellings is not merged; needs a curated list |
| Dependency vulnerability audit | P2 | pip-audit not available offline; npm audit not run against a live registry |
| `/filters` lists the top 200 values per field | P3 | 524 cities; the rest are reachable by search, not by checkbox |
| Admin token has no minimum length; `/api/docs` public; default Postgres password in Compose | P2 | Acceptable for local use only; harden before deploying |
| Localhost-only port binding | P2 | See §4.5; needs `127.0.0.1` in `DATABASE_URL` docs as well |
| Dockerfile pip cache mount | P3 | Builds failed repeatedly on PyPI timeouts; a BuildKit cache mount would help |
| Role misses (pengemudi, tentor, household workers) | P2 | Not changed, to keep the held-out evaluation honest; needs a new labelled sample |
| Two single outliers (posting date 2022-01-01, a 2029 deadline) | P3 | Single records rather than patterns; kept and visible |
