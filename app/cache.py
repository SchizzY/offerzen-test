import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from valkey.asyncio import Valkey
from valkey.exceptions import ValkeyError

from app.env import valkey_url

__all__ = [
    "Valkey",
    "ValkeyError",
    "connect",
    "create_client",
    "disconnect",
    "get_valkey",
    "valkey_client",
]

logger = logging.getLogger(__name__)

VALKEY_URL = valkey_url()

# Short, so a hung Valkey fails over to Postgres quickly instead of stalling requests.
CACHE_TIMEOUT = float(os.getenv("VALKEY_TIMEOUT", 1))

_client: Valkey | None = None


def create_client(url: str = VALKEY_URL) -> Valkey:
    return Valkey.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=CACHE_TIMEOUT,
        socket_timeout=CACHE_TIMEOUT,
    )


async def connect() -> Valkey:
    """Create the shared client. Valkey being down is not fatal: the client
    reconnects on its own and callers fall back to Postgres meanwhile."""
    global _client
    if _client is None:
        _client = create_client()
        try:
            await _client.ping()
        except (ValkeyError, OSError) as err:
            logger.warning("Valkey unreachable at startup (%s); continuing without cache", err)
    return _client


async def disconnect() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def get_valkey() -> Valkey:
    if _client is None:
        raise RuntimeError("Valkey is not connected; call app.cache.connect() first")
    return _client


@asynccontextmanager
async def valkey_client(url: str = VALKEY_URL) -> AsyncGenerator[Valkey, None]:
    client = create_client(url)
    try:
        yield client
    finally:
        await client.aclose()
