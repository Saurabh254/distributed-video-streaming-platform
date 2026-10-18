from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.dependencies import DbPoolDep, RedisDep, S3Dep

router = APIRouter(prefix="/healthz", tags=["health"])


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness():
    """Liveness probe: verifies process is alive."""
    return {"status": "ok"}


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness(redis_conn: RedisDep, db_pool: DbPoolDep, s3: S3Dep):
    """Readiness probe: verifies all infrastructure dependencies (DB, Redis, S3)."""
    checks: dict[str, str] = {}
    is_healthy = True

    # 1. PostgreSQL check
    try:
        async with db_pool.connection(timeout=2.0) as conn, conn.cursor() as cur:
            await cur.execute("SELECT 1")
        checks["postgres"] = "healthy"
    except Exception as exc:  # noqa: BLE001
        is_healthy = False
        checks["postgres"] = f"unhealthy: {exc}"

    # 2. Redis check
    try:
        await redis_conn.ping()
        checks["redis"] = "healthy"
    except Exception as exc:  # noqa: BLE001
        is_healthy = False
        checks["redis"] = f"unhealthy: {exc}"

    # 3. S3 check
    try:
        await s3.validate_connection()
        checks["s3"] = "healthy"
    except Exception as exc:  # noqa: BLE001
        is_healthy = False
        checks["s3"] = f"unhealthy: {exc}"

    overall_status = "healthy" if is_healthy else "unhealthy"
    status_code = (
        status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(
        status_code=status_code,
        content={"status": overall_status, "checks": checks},
    )
