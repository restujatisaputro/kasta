import logging
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from kasta_api import __version__
from kasta_api.api.dependencies import DatabaseSession
from kasta_api.core.errors import ProblemDetail

router = APIRouter()
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["kasta-api"] = "kasta-api"
    version: str = __version__
    timestamp: datetime


class ReadinessResponse(HealthResponse):
    database: Literal["ok"] = "ok"


def health_response() -> HealthResponse:
    return HealthResponse(timestamp=datetime.now(UTC))


@router.get("/live", response_model=HealthResponse, operation_id="getLiveness")
async def get_liveness() -> HealthResponse:
    """Return process liveness without calling an external dependency."""
    return health_response()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    operation_id="getReadiness",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ProblemDetail}},
)
async def get_readiness(session: DatabaseSession) -> ReadinessResponse:
    """Return readiness after verifying the PostgreSQL connection."""
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.warning("Database readiness check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database belum siap.",
        ) from exc
    return ReadinessResponse(timestamp=datetime.now(UTC))
