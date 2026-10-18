from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api import api_router
from app.core.config import settings
from app.core.lifespan import lifespan
from app.core.logging import RequestLoggingMiddleware, setup_logging

# Configure logging at module load
setup_logging()

app = FastAPI(
    title="AuraStream Playback Service",
    description="Video Playback Session Coordination and Stream Delivery Service",
    version="0.1.0",
    lifespan=lifespan,
)

# Logging & Correlation ID middleware
app.add_middleware(RequestLoggingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
