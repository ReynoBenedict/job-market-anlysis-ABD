# Testing

| Suite | Command | Needs |
|---|---|---|
| Backend unit (normalization, HTTP client, Lever parser, policy gate, lake parsing and pipeline) | `cd backend && pytest tests/unit` | nothing |
| Backend integration (migrations, pipeline, API) | `cd backend && pytest tests/integration` | PostgreSQL at `TEST_DATABASE_URL` (default `localhost:5433/talentscope_test`, created automatically) |
| Backend static checks | `ruff check talentscope tests && ruff format --check talentscope tests && mypy talentscope` | |
| Frontend unit/component | `cd frontend && npm test` | |
| Frontend static checks + build | `npm run lint && npm run typecheck && npm run build` | |
| End-to-end journeys | `cd frontend && API_BASE_URL=http://localhost:8010 npm run test:e2e` | running web + API; expected values are read from the API, so any dataset works; set `ADMIN_USERNAME`/`ADMIN_PASSWORD` to include admin journeys |

Integration tests run each test in a transaction that is rolled back; the schema is built
with the real Alembic migrations (downgrade to base, then upgrade). No test contacts an
external job site: network behaviour uses `httpx.MockTransport` and synthetic fixtures in
`backend/tests/fixtures/`.

## What is covered
- **Normalization:** Indonesian/English salary formats, decimal and thousands separators,
  single values, hidden/negotiable/unparseable/invalid salaries, stated vs. assumed
  periods, yearly→monthly conversion, unconverted hourly pay, USD, outlier flags;
  locations (structured, aliases, inferred, remote, city/province name clashes);
  employment type, experience, education, posting age ("UrgentKemarin"), card tags
  (truncation, Hybrid/Remote separation); punctuation and empty-token safety; URL
  validation; role-family rules.
- **Ingestion:** policy gate for every non-runnable status, pause, expired reviews;
  idempotent re-import; rejected records; schema change; partial runs after access
  denial; empty results; cross-source exact match; same-source look-alikes kept apart;
  observation-time ordering; content updates; registry sync not overriding newer decisions.
- **HTTP client:** User-Agent, per-host spacing, robots.txt allow/deny/unreachable,
  401/403 not retried, 5xx retried with backoff, 429 with Retry-After, non-JSON responses.
- **Lake (Common Crawl → silver → gold → app):** JSON-LD extraction (`@graph`, lists,
  CDATA, malformed blocks), WARC record parsing, JobPosting normalization (invalid
  reasons, salary units and currency aliases, dates, multi-location and remote,
  province/city resolution, title keys), skill dictionary including reviewed false
  positives, canonical URLs, domain policy; deduplication on a synthetic bronze fixture
  (exact, syndicated, reposted >45 days apart, fuzzy titles, city-templated pages),
  template-salary detection, idempotent and incremental silver rebuilds, re-observations,
  collector resume, stop on HTTP 403 with no further requests, retry of transient
  failures, later-excluded sites dropped, JSON Lines import (rejections, idempotency,
  source attribution), and idempotent publishing into PostgreSQL. All lake fixtures are
  synthetic and live in the tests; none reach `lake/`.
- **API:** filters (each dimension, combinations, LIKE-wildcard escaping), stable
  pagination, sorting with unknown salaries last, validation errors and envelope,
  404s, overview counts and scope, breakdown denominators, salary eligibility,
  withheld statistics for small groups, midpoint percentiles with yearly conversion and
  excluded hourly/USD pay, source tags, coverage, admin auth (missing/wrong/disabled
  token), pause audit trail, resume refusal.
- **Frontend unit:** formatting (id-ID), URL filter state, drill-down links, pagination
  window, axis ticks, admin Basic auth, bar list rendering, saved-job toggling.
- **E2E (Playwright, 2026-10-17 revamp):** ten journeys: (1) home statistics equal the
  API and search reaches results; (2) search + province + status filters combine, the
  total equals the API for the same URL, chip removal, reset, sort, page 2; (3) job detail
  equals the API (title, company, status notice, "never re-checked", original link
  target/rel), back link restores the search; (4) save → header count → saved page →
  reload → remove → reload; (5) salary summary follows filters and matches the API sample
  size, sparse groups show no numbers, table view; (6) market comparison total equals the
  API, a bar opens the doubly filtered search; (7) sources page separates active from
  unused sources, methodology detail is collapsed by default; (8) empty, invalid-parameter,
  and missing-record states; (9) phone menu and filter drawer; (10) API count consistency
  (overview = filters = search = Σ status = Σ sources). A layout test loads every page at
  1440×900, 1280×720, 1024×768, 768×1024, 390×844, 360×800 and fails on horizontal
  overflow or missing navigation.
- **Self-contained stack (`E2E_LOCAL_STACK=1`, project `local-stack`):** Playwright
  starts an API with a per-run, test-only admin token, a toggleable proxy in front of it
  (`e2e/support/toggle-proxy.mjs`), and a production web server with per-run admin
  credentials (nothing written to disk or committed). Tests: API outage shows the error
  state with a "Coba lagi" link (not an endless loading state) on the search page, the
  home page keeps search usable, a job page during an outage is not a false 404, and the
  app recovers when the API returns; admin journeys (wrong password rejected, audited
  pause/resume, blocked source cannot be resumed, run history with a policy-blocked run,
  data-quality page).
- **HTTP status:** a full page load of an unknown job returns 404 (journey 8).
- **Role taxonomy evaluation:** `talentscope roles sample|score` and
  `tests/unit/test_role_evaluation.py`; results in ML_EVALUATION.md §7.
- **Accessibility:** an ad-hoc axe-core audit (`node frontend/e2e/a11y.mjs`) over all
  pages; results are recorded in the final report, not enforced in CI.
- **E2E (earlier journeys, partly superseded):** search from home → detail; filter + chip removal; salary sort and
  pagination; empty state; invalid parameter error state; save/unsave; overview
  drill-down; salary page sample sizes, comparison switch, table view; source registry;
  admin auth; admin pause/resume with audit; blocked source has no resume control; run
  history/quality pages; mobile navigation without horizontal overflow.

## Not covered (known gaps)
- Formal role-taxonomy precision on a labelled sample (only a 40-title spot check).
- Accessibility audit with assistive technology (semantic structure and focus states were
  built in; no axe/screen-reader run was recorded).
- Load testing.
- Client-side navigation (not a full page load) to an unknown job renders the not-found
  page without a 404 status (the proxy only answers full page loads).
- The admin journeys pause and resume the snapshot source in the database they run
  against; they leave append-only audit entries.
- Lake collection against the live archive is exercised by real runs (docs/DATA_INVENTORY.md),
  not by automated tests; tests never contact Common Crawl.
- Precision of skill dictionary `skills-2026.10.3` was not re-measured after the fixes
  (docs/ml/SKILL_EXTRACTION_REVIEW.md).
