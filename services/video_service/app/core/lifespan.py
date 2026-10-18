import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.connectors.postgres import db_manager
from app.core.connectors.redis import redis_manager
from app.core.connectors.s3 import s3_manager
from app.db.init_db import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Suppress raw unstructured uvicorn access logs
    logging.getLogger("uvicorn.access").disabled = True

    # 1. Connect Redis
    await redis_manager.start()

    # 2. Connect Database & initialize schema
    try:
        await db_manager.start()
        await init_db(db_manager)

        # 3. Initialize S3 client and ensure bucket & CORS configuration
        s3_manager.start()
        await s3_manager.ensure_bucket_and_cors(settings.s3_bucket)

        yield
    finally:
        await db_manager.close()
        await redis_manager.close()
