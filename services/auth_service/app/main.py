import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api import auth_app
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.core.lifespan import lifespan
from app.core.logging import RequestLoggingMiddleware, setup_logging

# Initialize production logging configuration
setup_logging()

app = FastAPI(
    title="fineshare",
    version="0.0.1",
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
app.include_router(health_router)
app.include_router(auth_app)

if __name__ == "__main__":
    uvicorn.run(app)
