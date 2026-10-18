from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import Depends
from redis.asyncio import Redis

from app.core.connectors.postgres import db_manager
from app.core.connectors.redis import redis_manager


async def get_db_connection() -> AsyncIterator[Any]:
    """Dependency that provides a PostgreSQL connection from the pool."""
    async with db_manager.get_connection() as conn:
        yield conn


def get_redis() -> Redis:
    """Dependency that provides the Redis client instance."""
    return redis_manager.get_client()


DbConnectionDep = Annotated[Any, Depends(get_db_connection)]
RedisDep = Annotated[Redis, Depends(get_redis)]
