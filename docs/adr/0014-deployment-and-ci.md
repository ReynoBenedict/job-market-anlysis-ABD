# ADR-0014: Deployment, CI, and testing

**Status:** accepted (2026-10-17)

- **Docker Compose** with three services (db, api, web). Images run as non-root users.
  The API container applies migrations at start; data import is an explicit one-off
  (`docker compose run --rm api talentscope bootstrap`) so a restart never re-imports.
- **GitHub Actions** (`.github/workflows/ci.yml`): backend lint/format/mypy/pytest against a
  Postgres service; frontend lint/typecheck/Vitest/build; Playwright journeys against
  the built app with the snapshot imported.
- Tests never call external job sites; network connectors are tested with
  `httpx.MockTransport` and synthetic fixtures.
- Kubernetes and managed cloud services are out of scope; any VM with Docker can run
  the stack (docs/DEPLOYMENT.md).
