import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.connectors.postgres import db_manager
from app.core.connectors.redis import redis_manager
from app.core.connectors.s3 import s3_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manages application startup and shutdown lifecycle events."""
    logger.info("Initializing Playback Service dependencies...")

    # Start PostgreSQL Connection Pool
    await db_manager.start()

    # Start Redis connection
    await redis_manager.start()

    # Start S3 Client
    s3_manager.start()
    try:
        await s3_manager.validate_connection()
    except Exception as e:
        logger.warning("S3 initial validation notice: %s", e)

    logger.info("Playback Service startup complete")
    yield

    logger.info("Shutting down Playback Service...")
    await redis_manager.close()
    await db_manager.close()
    logger.info("Playback Service shutdown complete")
