import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.connectors.postgres import db_manager
from app.core.connectors.redis import redis_manager
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Disable raw unstructured uvicorn access logs in favor of structured RequestLoggingMiddleware
    logging.getLogger("uvicorn.access").disabled = True

    await redis_manager.start()
    try:
        await db_manager.start()
        await init_db(db_manager)
        yield
    finally:
        await db_manager.close()
        await redis_manager.close()
