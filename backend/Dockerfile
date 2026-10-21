# Build context: repository root (see docker-compose.yml), so the image can include the
# historical snapshot and the reviewed source matrix used by `talentscope bootstrap`.
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY backend/pyproject.toml backend/pyproject.toml
COPY backend/talentscope backend/talentscope
RUN pip install ./backend

# Read-only inputs for `talentscope bootstrap`; paths match the defaults used on a host.
COPY data/raw/glints_jobs.csv data/raw/glints_jobs.csv
COPY docs/research/source_matrix.json docs/research/source_matrix.json

RUN useradd --system --uid 10001 talentscope
USER talentscope

EXPOSE 8000
# Apply migrations, then serve. Importing data is an explicit one-off step:
#   docker compose run --rm api talentscope bootstrap
CMD ["sh", "-c", "talentscope db upgrade && exec uvicorn --factory talentscope.api.app:create_app --host 0.0.0.0 --port 8000 --proxy-headers"]
