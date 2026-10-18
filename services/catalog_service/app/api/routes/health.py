from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.connectors.postgres import db_manager
from app.core.connectors.redis import redis_manager

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
async def health_check() -> JSONResponse:
    """Performs deep health checks on PostgreSQL and Redis dependencies."""
    pg_healthy = False
    redis_healthy = False

    try:
        pg_healthy = await db_manager.validate_connection()
    except Exception:
        pg_healthy = False

    try:
        redis_healthy = await redis_manager.validate_connection()
    except Exception:
        redis_healthy = False

    is_overall_healthy = pg_healthy and redis_healthy
    status_code = (
        status.HTTP_200_OK
        if is_overall_healthy
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if is_overall_healthy else "unhealthy",
            "service": "catalog-service",
            "dependencies": {
                "postgres": "connected" if pg_healthy else "unreachable",
                "redis": "connected" if redis_healthy else "unreachable",
            },
        },
    )
