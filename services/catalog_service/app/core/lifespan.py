import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.connectors.postgres import db_manager
from app.core.connectors.redis import redis_manager
from app.db.init_db import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manages application startup and shutdown lifecycle events."""
    logger.info("Initializing Catalog Service dependencies...")

    # Start PostgreSQL Connection Pool
    await db_manager.start()

    # Initialize Catalog DB Tables/Columns
    await init_db(db_manager)

    # Start Redis connection
    await redis_manager.start()

    logger.info("Catalog Service startup complete")
    yield

    logger.info("Shutting down Catalog Service...")
    await redis_manager.close()
    await db_manager.close()
    logger.info("Catalog Service shutdown complete")
