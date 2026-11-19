from fastapi import APIRouter, Depends, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.cache import Valkey, ValkeyError, get_valkey
from app.db import get_session
from app.schemas.common import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    operation_id="getHealth",
    summary="Check API health",
    description=(
        "200 when Postgres is up, even if Valkey is down (`degraded`): orders are "
        "still accepted then. 503 only when Postgres is down."
    ),
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": HealthResponse,
            "description": "Postgres is down",
        }
    },
)
async def health(
    response: Response,
    cache: Valkey = Depends(get_valkey),
    session: Session = Depends(get_session),
) -> HealthResponse:
    try:
        await run_in_threadpool(session.execute, text("SELECT 1"))
        database = "ok"
    except SQLAlchemyError:
        database = "down"

    try:
        await cache.ping()
        valkey = "ok"
    except (ValkeyError, OSError):
        valkey = "down"

    if database == "down":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        overall = "down"
    else:
        overall = "ok" if valkey == "ok" else "degraded"
    return HealthResponse(status=overall, database=database, valkey=valkey)
