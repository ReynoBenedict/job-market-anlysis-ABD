# ADR-0001: Modular monolith

**Status:** accepted (2026-10-17)

## Context
The data is one historical snapshot of 1,133 rows; no permitted live source exists yet
(docs/RESEARCH_SOURCES.md). One developer maintains the project. The SRS asks for clear
boundaries between presentation, API, persistence, ingestion, normalization, and
analytics, without premature distribution.

## Options
1. Microservices (separate ingestion, analytics, API, search services).
2. A single Python web framework rendering HTML (e.g. Django templates).
3. One repository with a Python backend package and a separate Next.js web app.

## Decision
Option 3. `backend/talentscope` is one installable package whose modules map to the
SRS boundaries (`ingestion`, `normalization`, `analytics`, `api`, `sources`, `models`).
It runs as one API process; batch work (imports, connector runs) uses the same package
through the `talentscope` CLI. The web app is a separate process because it renders
React server components and is deployed as a Node server.

## Consequences
- Three processes in production: web, API, PostgreSQL. No queue, cache, or search engine.
- Business rules exist once, in Python; the web app receives Indonesian labels from the API.
- Revisit if ingestion becomes long-running enough to need a worker separate from the API.
