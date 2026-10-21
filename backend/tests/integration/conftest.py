"""Integration tests run against a real PostgreSQL database (``TEST_DATABASE_URL``).

The database is created if missing and migrated with Alembic, so the migrations are
tested too. Each test runs inside a transaction that is rolled back afterwards; code
under test may call ``commit()``, which only releases a savepoint.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from talentscope.api.app import create_app
from talentscope.api.deps import get_session
from talentscope.config import Settings, get_settings
from talentscope.models import Source
from talentscope.vocab import PermissionStatus

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://talentscope:talentscope@localhost:5433/talentscope_test",
)
FIXTURES = Path(__file__).parents[1] / "fixtures"
ADMIN_TOKEN = "test-admin-token"
SNAPSHOT_OBSERVED_AT = datetime(2026, 6, 12, 19, 57, 2, tzinfo=timezone.utc)


def _ensure_database(url: str) -> None:
    target = make_url(url)
    admin_engine = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            exists = conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": target.database}
            )
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    except OperationalError as exc:
        pytest.exit(
            f"Integration tests need PostgreSQL at {target.render_as_string(hide_password=True)}. "
            "Start it with `docker compose up -d db` or set TEST_DATABASE_URL.\n"
            f"{type(exc).__name__}: {exc.orig}",
            returncode=2,
        )
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    _ensure_database(TEST_DATABASE_URL)
    config = Config()
    config.set_main_option("script_location", "talentscope:migrations")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    outer = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield db
    finally:
        db.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url=TEST_DATABASE_URL, admin_api_token=ADMIN_TOKEN, freshness_window_days=30
    )


@pytest.fixture
def client(session: Session, settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as test_client:
        yield test_client


def make_source(
    session: Session, source_id: str, status: PermissionStatus, **fields: object
) -> Source:
    source = Source(
        id=source_id,
        name=fields.pop("name", source_id.title()),
        category=fields.pop("category", "dataset"),
        permission_status=status.value,
        technical_method=fields.pop("technical_method", "manual_import"),
        connector_config=fields.pop("connector_config", {}),
        reviewed_at=fields.pop("reviewed_at", datetime(2026, 10, 1, tzinfo=timezone.utc)),
        **fields,
    )
    session.add(source)
    session.flush()
    return source
