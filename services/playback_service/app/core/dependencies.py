from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import Depends, Request
from redis.asyncio import Redis

from app.core.connectors.postgres import db_manager
from app.core.connectors.redis import redis_manager
from app.core.connectors.s3 import S3Manager, s3_manager
from app.core.security import extract_user_id_from_request


async def get_db_connection() -> AsyncIterator[Any]:
    """Dependency that provides a PostgreSQL connection from the pool."""
    async with db_manager.get_connection() as conn:
        yield conn


def get_redis() -> Redis:
    """Dependency that provides the Redis client instance."""
    return redis_manager.get_client()


def get_s3() -> S3Manager:
    """Dependency that provides the S3 manager."""
    return s3_manager


def get_optional_user_id(request: Request) -> str | None:
    """Dependency that extracts user_id from Bearer token if supplied."""
    return extract_user_id_from_request(request)


DbConnectionDep = Annotated[Any, Depends(get_db_connection)]
RedisDep = Annotated[Redis, Depends(get_redis)]
S3Dep = Annotated[S3Manager, Depends(get_s3)]
OptionalUserIdDep = Annotated[str | None, Depends(get_optional_user_id)]
