"""Integration tests against real Postgres and Valkey (start them: ./scripts/up.sh).

They never touch your dev data: they use their own database, <POSTGRES_DB>_test
(created and migrated automatically), and Valkey DB 1. Every test starts from a
clean, seeded state. The app runs in-process with its stock worker and cache
sync, exactly as in production.

Override with TEST_POSTGRES_DB / TEST_VALKEY_DB if needed.
"""

import os
import urllib.parse
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

# Point the app at the test instances BEFORE anything imports app.db / app.cache.
from app.env import database_url, valkey_url  # only loads .env; connects to nothing

ROOT = Path(__file__).resolve().parent.parent

_dev_url = make_url(database_url())
TEST_DB = os.getenv("TEST_POSTGRES_DB", f"{_dev_url.database}_test")
if TEST_DB == _dev_url.database:
    raise RuntimeError(f"Refusing to run tests against the dev database {TEST_DB!r}")
TEST_DATABASE_URL = _dev_url.set(database=TEST_DB).render_as_string(hide_password=False)

_valkey = urllib.parse.urlsplit(valkey_url())
TEST_VALKEY_URL = urllib.parse.urlunsplit(_valkey._replace(path=f"/{os.getenv('TEST_VALKEY_DB', '1')}"))

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["VALKEY_URL"] = TEST_VALKEY_URL
# Faster polling keeps the tests quick; the wake-up signal does most of the work.
os.environ["STOCK_WORKER_POLL"] = "0.2"
os.environ["EVENT_STREAM_POLL"] = "0.2"
os.environ["CACHE_SYNC_INTERVAL"] = "1"


def _ensure_test_database() -> None:
    admin = create_engine(_dev_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DB})
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
    except OperationalError as err:
        pytest.exit(f"Postgres isn't reachable ({err.orig}). Start it with ./scripts/up.sh", returncode=2)
    finally:
        admin.dispose()


def _migrate() -> None:
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")


@pytest.fixture(scope="session")
def client():
    """The app, with its lifespan running (stock worker, cache sync)."""
    _ensure_test_database()
    _migrate()

    from valkey import Valkey
    from valkey.exceptions import ValkeyError

    try:
        Valkey.from_url(TEST_VALKEY_URL).ping()
    except (ValkeyError, OSError) as err:
        pytest.exit(f"Valkey isn't reachable ({err}). Start it with ./scripts/up.sh", returncode=2)

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_state(client):
    """Fresh, seeded data and an empty cache for every test."""
    from valkey import Valkey

    from app.stock_worker import set_paused
    from scripts.reset import reset_database

    set_paused(False)
    reset_database()
    Valkey.from_url(TEST_VALKEY_URL).flushdb()
    yield
    set_paused(False)  # never leave the worker paused for the next test
