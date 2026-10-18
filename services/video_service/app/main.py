import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api import api_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.core.lifespan import lifespan
from app.core.logging import RequestLoggingMiddleware, setup_logging

# Initialize structured logging configuration
setup_logging()

app = FastAPI(
    title="video-service",
    description="Video Upload & Ingestion Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root-level health probe
app.include_router(health_router)

# Video APIs
app.include_router(api_router)


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
