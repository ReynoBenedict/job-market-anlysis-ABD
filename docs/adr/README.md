# Architecture Decision Records

Short records of significant decisions: context, options, decision, consequences, and
what would make us revisit it. Numbering follows SRS §24.

| ADR | Decision |
|---|---|
| [0001](0001-modular-monolith.md) | One repository, three runtime processes (web, API, Postgres) plus CLI batch jobs |
| [0002](0002-frontend-stack.md) | Next.js 16 + React 19 + TypeScript + Tailwind v4; hand-built SVG/HTML charts |
| [0003](0003-api-and-persistence.md) | FastAPI + Pydantic + SQLAlchemy 2 (sync) + Alembic |
| [0004](0004-data-model-and-search.md) | Postgres; canonical jobs vs. source records; pg_trgm search |
| [0005](0005-source-connectors.md) | Small adapter interface over httpx, not Scrapy |
| [0006](0006-browser-automation-policy.md) | No browser automation; legacy Selenium scraper disabled |
| [0007](0007-scheduling.md) | CLI runs, no scheduler/orchestrator yet |
| [0008](0008-analytics-engine.md) | Online analytics in SQL; Spark kept for batch ML evaluation only |
| [0009](0009-storage-and-retention.md) | Raw files are read-only; minimal raw fields in JSONB; no HTML retained |
| [0010](0010-identity-and-deduplication.md) | Source key identity, conservative exact-fingerprint cross-source matching |
| [0011](0011-skills.md) | No skill analytics from truncated tags; dictionary extraction deferred |
| [0012](0012-career-matching.md) | Career matching deferred until skill data exists |
| [0013](0013-auth-and-privacy.md) | No user accounts; admin via Basic auth (web) + bearer token (API) |
| [0014](0014-deployment-and-ci.md) | Docker Compose, GitHub Actions, real-Postgres tests |
| [0015](0015-data-lake.md) | Parquet bronze/silver/gold lake with DuckDB; Common Crawl JobPosting archive as the first bulk source. Partly supersedes 0008 and 0009; implements 0011's dictionary baseline |
