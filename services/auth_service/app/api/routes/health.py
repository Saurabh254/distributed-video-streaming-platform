from app.core.dependencies import RedisDep
from app.services.health_service import evaluate_system_health
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/healthz", tags=["health"])


@router.get("", status_code=status.HTTP_200_OK)
async def healthz(redis_conn: RedisDep):
    report = await evaluate_system_health(redis_conn)

    if report["status"] != "healthy":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=report,
        )

    return report
