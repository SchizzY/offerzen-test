"""Settings: load .env, and build the connection URLs from it.

Real environment variables win over .env, so `FOO=1 poetry run ...` still works.
Create your .env with ./scripts/init-env.sh (it copies .env.example).

Nothing here connects to anything, so it is safe to import first (the tests
point DATABASE_URL / VALKEY_URL at test instances before the app is imported).
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

load_dotenv(ENV_FILE, override=False)


def database_url() -> str:
    """DATABASE_URL if set, else built from the POSTGRES_* settings (the same
    ones docker-compose.yml uses to create the database)."""
    return os.getenv("DATABASE_URL") or URL.create(
        "postgresql+psycopg",
        username=os.getenv("POSTGRES_USER", "admin"),
        password=os.getenv("POSTGRES_PASSWORD", "admin"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5433)),
        database=os.getenv("POSTGRES_DB", "offerzen-db"),
    ).render_as_string(hide_password=False)


def valkey_url() -> str:
    """VALKEY_URL if set, else built from VALKEY_HOST / VALKEY_PORT."""
    return os.getenv("VALKEY_URL") or (
        f"valkey://{os.getenv('VALKEY_HOST', 'localhost')}:{os.getenv('VALKEY_PORT', 6380)}/0"
    )
