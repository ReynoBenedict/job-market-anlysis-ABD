# TalentScope

**Indonesian labour-market intelligence: job search, market and salary analytics with
transparent sources and limitations.** The user interface is in Bahasa Indonesia; code
and engineering docs are in English.

TalentScope grew out of an academic Big Data project (Spark SQL + MLlib on 1,133 Glints
listings). It keeps that data and analysis, re-engineered as a tested web application
with a policy-gated ingestion pipeline and a Parquet data lake. It does **not** scrape
job sites: every source must pass a documented permission review first, and none of the
27 job-listing sources researched allows automated collection. Volume comes from Common
Crawl's public web archive instead: archived `.id` pages that publish schema.org
JobPosting data, minus sites whose terms prohibit it (see [Data sources](#data-sources)).

## What works today
One consistent site (top navigation, mobile menu) in Bahasa Indonesia:
- **Beranda** (`/`): search with examples, an honest summary of what the data is (how many
  listings, from which sources, how many already expired), and a few findings computed live.
- **Cari Lowongan** (`/lowongan`): search title/company/location; filters for status,
  province, city, field, employment type, work arrangement, experience, education, source,
  monthly salary; sorting (non-expired first by default); pagination; all state in the URL.
  Compact cards show salary, status, posting date, and the original site.
- **Detail lowongan** (`/lowongan/[id]`): status explained up front ("Batas lamaran sudah
  lewat" / "Belum tentu masih dibuka"), posting date, deadline, archive date, "diperiksa
  langsung: belum pernah", link to the original page (http/https only), the original title
  when it was cleaned, and a link back to the same search results.
- **Gaji** (`/gaji`): the median and middle range first in plain words, comparison by
  field/province/experience/type/education with sample sizes, distribution, filters.
- **Pasar Kerja** (`/ringkasan`, `/pasar`): fields, provinces, cities, employers; every bar
  opens the matching jobs; `/pasar` recomputes everything for chosen filters.
- **Keterampilan** (`/keterampilan`): what can and cannot be said about skills yet.
- **Tersimpan** (`/tersimpan`): saved jobs in this browser only, with their status when saved.
- **Sumber Data** and **Cara Kami Menghitung** (`/sumber-data`, `/metodologi`): sources in
  use vs. examined-but-unused (blocked, needs permission, unreviewed); short answers with
  details behind "Rincian".
- **Admin workspace** (`/admin`, Basic auth): source registry with audited pause/resume,
  ingestion run history, data-quality report, audit log.
- **Ingestion pipeline** (`talentscope` CLI): policy gate, idempotent upserts, provenance,
  run records with categorized failures, a polite HTTP client, and a Lever API connector
  (implemented and tested, **disabled** pending employer consent).

**Status of a listing.** TalentScope never re-checks listings live, so nothing is labelled
"open". Each job is *Kedaluwarsa menurut sumber* (deadline passed), *Riwayat lowongan*
(older observation, status unknown), or *Baru terlihat, belum diverifikasi* (seen within
30 days). Today: 5,227 expired, 2,080 history, 0 recent.

- **Data lake** (`talentscope lake ...`, [docs/LAKE.md](docs/LAKE.md)):
  - collection from the Common Crawl archive (rate-limited, resumable, stops on 403/429);
  - bronze/silver/gold Parquet layers built with DuckDB;
  - validation and deduplication of reposts, syndication, fuzzy titles and SEO city pages
    into canonical vacancies;
  - template-salary detection, dictionary skill extraction, and a data-quality report;
  - a JSON Lines import path for licensed feeds;
  - publishing into the app.
- **Real data now:** 7,307 jobs in the app = 6,174 unique canonical vacancies from three
  archive crawls + the 1,133-listing snapshot ([docs/DATA_INVENTORY.md](docs/DATA_INVENTORY.md)). The
  100,000 target is not reached; the gap and the realistic path are documented there and
  in [docs/SOURCE_ACQUISITION.md](docs/SOURCE_ACQUISITION.md).

Not built (by decision, see `docs/adr/`): user accounts, career matching, skill rankings
(data not yet adequate), trend charts, live collection or verification of listings.

## Architecture
Next.js 16 web app → FastAPI API → PostgreSQL 16, plus CLI batch jobs. Details:
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), decisions: [docs/adr/](docs/adr/README.md).

| Layer | Technology | Why |
|---|---|---|
| Web | Next.js 16, React 19, TypeScript, Tailwind v4, lucide icons | Server-rendered, URL state, API stays server-side |
| API | FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, psycopg 3 | Typed validation + OpenAPI; same language as the pipeline |
| Data | PostgreSQL 16 + pg_trgm | Filters, percentiles, substring search at this scale without extra services |
| Lake | Parquet + DuckDB, CLI-orchestrated | Faster and leaner than local Spark at every size measured up to 5M rows ([docs/BENCHMARKS.md](docs/BENCHMARKS.md)) |
| Batch/ML | PySpark (offline evaluation, benchmark) | Reproduces the academic MLlib experiment; documented scale-out path for the lake |
| Ops | Docker Compose, GitHub Actions | Reproducible three-service stack |

## Quick start (Docker)
Requires Docker with Compose.
```bash
cp .env.example .env    # optionally set ADMIN_API_TOKEN, ADMIN_USERNAME, ADMIN_PASSWORD
docker compose up -d --build
docker compose run --rm api talentscope bootstrap   # migrate, register sources, import snapshot
```
Open http://localhost:3001 (web), http://localhost:8010/api/docs (API docs). Default
host ports are 5433 (Postgres), 8010 (API), and 3001 (web) to avoid common clashes;
change them in `.env`.

**Restart after code changes** (keeps the database volume `pgdata`):
```bash
docker compose up -d --build --no-deps api web
```
**Reload the archive data** into the app after a lake rebuild:
`DATABASE_URL=postgresql+psycopg://talentscope:talentscope@localhost:5433/talentscope talentscope lake run --publish`.

### Windows PowerShell
Run from the repository root (verified on Windows 11, PowerShell 5.1, 2026-10-18):
```powershell
# Database connection for the CLI (this terminal session only)
$env:DATABASE_URL = "postgresql+psycopg://talentscope:talentscope@localhost:5433/talentscope"
$env:PYTHONIOENCODING = "utf-8"            # Indonesian text in console output

# Rebuild the lake (silver -> gold) and publish to the app; safe to repeat
.\backend\.venv\Scripts\talentscope.exe lake run --publish
.\backend\.venv\Scripts\talentscope.exe lake report     # inventory as JSON

# Restart the app after code changes (database volume is kept)
docker compose up -d --build --no-deps api web
docker compose ps

# Regenerate the web API types (API must be running)
cd frontend; $env:API_BASE_URL = "http://localhost:8010"; npm run gen:api; cd ..
```

## Local development
Prerequisites: Python 3.10+, Node.js 22, Docker (for PostgreSQL).
```bash
docker compose up -d db

# Backend
cd backend
python -m venv .venv && .venv/Scripts/activate   # Windows; use .venv/bin/activate on macOS/Linux
pip install -e ".[dev]"
cd ..
export DATABASE_URL=postgresql+psycopg://talentscope:talentscope@localhost:5433/talentscope
talentscope bootstrap                       # run from the repository root
uvicorn --factory talentscope.api.app:create_app --port 8010 --reload

# Frontend (new terminal)
cd frontend
npm ci
echo "API_BASE_URL=http://localhost:8010" > .env.local
npm run dev                                 # http://localhost:3001
```
After changing API schemas, regenerate the web types with `npm run gen:api`.

## Tests
```bash
cd backend && pytest                  # integration tests need the db container
ruff check talentscope tests && mypy talentscope
cd frontend && npm test && npm run lint && npm run typecheck && npm run build
API_BASE_URL=http://localhost:8010 npm run test:e2e   # journeys incl. 6 viewport sizes
E2E_LOCAL_STACK=1 API_BASE_URL=http://localhost:8010 npx playwright test --project=local-stack
#   ^ admin journeys + API outage/recovery on a self-contained stack with per-run test credentials
#     (needs `npm run build`; in PowerShell set the variables with $env:NAME = "value")
```
See [docs/TESTING.md](docs/TESTING.md) for coverage and known gaps.

## Data sources
| Source | Status | In the app |
|---|---|---|
| Glints snapshot, June 2026 (historical, academic) | Historical data; right to republish not confirmed (collected by a scraper, no permission on record) | 1,133 listings, labelled historical |
| Common Crawl archive, `.id` pages with JobPosting markup | Research use with conditions (site exclusions, no descriptions shown, ≤2 req/s) | 6,174 canonical vacancies (archived; not presented as open) |
| Glints (live) | Blocked: terms prohibit scraping without written consent | – |
| JobStreet, LinkedIn, Indeed, KitaLulus, Karir.com, Pasker ID | Blocked by their terms | – |
| Kalibrr, Pintarnya, Karirhub, ATS APIs (Lever, Greenhouse, Ashby, SmartRecruiters, Workday) | Require written permission | – |
| Dealls, Loker.id, TopKarir, HiredToday, Tech in Asia, SSCASN, data portals | Need review | – |

Evidence, quotes, and review dates: [docs/RESEARCH_SOURCES.md](docs/RESEARCH_SOURCES.md).
Policy: [docs/DATA_POLICY.md](docs/DATA_POLICY.md). Not legal advice.

## Known limitations
- **No listing is verified as currently open.** 71.5% have a deadline in the past; the
  rest are history with unknown status.
- Archive vacancies come mostly from ~10 regional vacancy sites (97%); large portals are
  excluded by policy, so coverage is uneven by region and occupation.
- Only 13% of archive vacancies have a salary usable for statistics (sites that print one
  template salary everywhere are excluded).
- The snapshot is keyword-sampled (≤ 13 June 2026, mostly tech/business), without URLs,
  descriptions, or exact dates; its salary period is assumed monthly and flagged.
- Role fields come from title rules (taxonomy 2026.10.5). On a held-out sample of 200
  titles labelled by two AI reviewers (no human annotator): coverage 84%, precision 94.6%,
  recall 84.6%; on the 161 titles not seen during tuning, precision 93.0% and recall 80.5%
  ([docs/ML_EVALUATION.md](docs/ML_EVALUATION.md) §7). Not human-validated.
- No skill rankings: data is not adequate yet ([docs/DATA_INVENTORY.md](docs/DATA_INVENTORY.md)).
- Saved jobs live in one browser and are not synchronized.
- Before deploying publicly, confirm the right to republish individual listings
  ([docs/DATA_POLICY.md](docs/DATA_POLICY.md)).

Next steps: [docs/ROADMAP.md](docs/ROADMAP.md).

## Repository layout
```
backend/      FastAPI app, ingestion pipeline, normalization, analytics, migrations, tests
frontend/     Next.js web app, unit tests (Vitest), journeys (Playwright)
analytics/    Offline PySpark evaluation of the clustering experiment
data/         Original snapshot (raw, read-only) and the legacy processed CSVs
docs/         Architecture, ADRs, data dictionary/policy, research, lake, inventory, benchmarks, API, testing
lake/         Local data lake (git-ignored; created by `talentscope lake ...`)
legacy/       The original academic pipeline (scraper disabled)
TALENTSCOPE_SRS.md   Requirements specification
```
