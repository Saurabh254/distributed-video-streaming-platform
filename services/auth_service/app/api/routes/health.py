from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.dependencies import DbPoolDep, RedisDep
from app.services.health_service import evaluate_system_health

router = APIRouter(prefix="/healthz", tags=["health"])


@router.get("", status_code=status.HTTP_200_OK)
async def healthz(redis_conn: RedisDep, db_pool: DbPoolDep):
    report = await evaluate_system_health(redis_conn=redis_conn, pg_conn=db_pool)

    if report["status"] != "healthy":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=report,
        )

    return report
