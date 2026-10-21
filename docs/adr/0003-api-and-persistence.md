# ADR-0003: API framework and persistence

**Status:** accepted (2026-10-17)

## Context
The existing project is Python. Ingestion, normalization, and analytics are Python. The
API must validate inputs, document itself, and return stable error envelopes.

## Decision
- **FastAPI + Pydantic v2** for routes, validation, and OpenAPI (`/api/docs`).
- **SQLAlchemy 2.0, synchronous**, with psycopg 3. Request volume is small; sync code is
  simpler to reason about and test. FastAPI runs sync endpoints in its thread pool.
- **Alembic** migrations, shipped inside the package so `talentscope db upgrade` works in
  the container without the source tree.
- Configuration via `pydantic-settings`; `DATABASE_URL` is required (fail fast).

## Consequences
- Integration tests run against real PostgreSQL (percentiles, trigram search, arrays).
- Revisit async only if endpoints start calling slow external services.
