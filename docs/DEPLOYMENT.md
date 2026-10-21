# Deployment

The supported deployment is Docker Compose on a single host.

```bash
cp .env.example .env            # set POSTGRES_PASSWORD, ADMIN_* values
docker compose up -d --build    # db, api (runs migrations on start), web
docker compose run --rm api talentscope bootstrap   # one-off: register sources, import snapshot
```

| Service | Image | Port (host) | Notes |
|---|---|---|---|
| db | postgres:16-alpine | `POSTGRES_PORT` (5433) | volume `pgdata` |
| api | `backend/Dockerfile` (python:3.10-slim, non-root) | `API_PORT` (8010) | JSON logs; `/api/v1/health` healthcheck |
| web | `frontend/Dockerfile` (node:22-alpine, Next standalone, non-root) | `WEB_PORT` (3001) | talks to `http://api:8000` inside the network |

## Configuration
See `.env.example`. `DATABASE_URL` is required by the API. The admin API is off unless
`ADMIN_API_TOKEN` is set; admin pages are off unless `ADMIN_USERNAME`,
`ADMIN_PASSWORD`, and `ADMIN_API_TOKEN` are all set. Secrets come only from the
environment; none are baked into images (the web build needs no API or secrets).

## Production notes
- Put a TLS-terminating reverse proxy (Caddy, nginx) in front of `web`; expose `api` only
  if third parties need it. Basic auth for `/admin` must only travel over HTTPS.
- Set `CORS_ORIGINS` to the public web origin if the API is exposed.
- Back up with `pg_dump` (see docs/PIPELINE.md). Migrations run automatically on API start.
- **Data rights:** review docs/DATA_POLICY.md before exposing the historical snapshot publicly.

## Without Docker
See README "Local development": Postgres via `docker compose up -d db`, the API with
uvicorn from `backend/.venv`, and the web app with `npm run dev`.
