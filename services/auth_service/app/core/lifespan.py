from contextlib import asynccontextmanager

from fastapi import FastAPI
from services.auth_service.app.core.connectors.redis import redis_manager


@asynccontextmanager
async def lifespan(app: FastAPI):

    await redis_manager.start()
    try:
        yield
    finally:
        await redis_manager.close()
