"""Health check API routes."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.config import Settings, get_settings
from app.db import connection
from app.models.schemas import HealthResponse
from app.services.cache import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Return the backend health status."""
    services = {
        "database": await _database_status(settings),
        "redis": await _redis_status(),
        "llm": "configured" if settings.deepseek_api_key else "not_configured",
    }
    status = (
        "ok"
        if all(value in {"connected", "configured"} for value in services.values())
        else "degraded"
    )
    return HealthResponse(status=status, services=services)


async def _database_status(settings: Settings) -> str:
    """Probe PostgreSQL with a minimal query."""
    try:
        if connection.async_session_factory is None:
            await connection.init_db(settings)

        if connection.async_session_factory is None:
            return "unavailable"

        async with connection.async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return "connected"
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        return "unavailable"


async def _redis_status() -> str:
    """Probe Redis with PING."""
    try:
        if await get_redis_client().ping():
            return "connected"
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
    return "unavailable"
