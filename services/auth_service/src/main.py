import uvicorn
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from src import api
from src.core.dependencies import RedisDep
from src.core.health import evaluate_system_health
from src.core.lifespan import lifespan

app = FastAPI(
    telemetry={"tracing": True}, title="fineshare", version="0.0.1", lifespan=lifespan
)


@app.get("/healthz", status_code=status.HTTP_200_OK)
async def healthz(redis_conn: RedisDep):
    report = await evaluate_system_health(redis_conn)

    if report["status"] != "healthy":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=report,
        )

    return report


app.mount("", api.auth_app)
if __name__ == "__main__":
    uvicorn.run(app)
