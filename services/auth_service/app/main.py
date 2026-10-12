import uvicorn
from app.core.dependencies import RedisDep
from services.auth_service.app.services.health_service import evaluate_system_health
from app.core.lifespan import lifespan
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from src import api

app = FastAPI(
    telemetry={"tracing": True}, title="fineshare", version="0.0.1", lifespan=lifespan
)





app.mount("", api.auth_app)
if __name__ == "__main__":
    uvicorn.run(app)
