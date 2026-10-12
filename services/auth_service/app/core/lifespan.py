from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.connectors.postgres import db_manager
from app.core.connectors.redis import redis_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_manager.start()
    try:
        await db_manager.start()
        yield
    finally:
        await db_manager.close()
        await redis_manager.close()
