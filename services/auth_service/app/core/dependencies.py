from collections.abc import AsyncIterator
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from app.core.connectors.postgres import db_manager
from app.core.connectors.redis import redis_manager

RedisDep = Annotated[aioredis.Redis, Depends(redis_manager.get_client)]


async def get_db_connection() -> AsyncIterator[AsyncConnection]:
    """Dependency that borrows a PostgreSQL connection from the pool for a request and releases it upon completion."""
    async with db_manager.get_connection() as conn:
        yield conn


def get_db_pool() -> AsyncConnectionPool:
    """Dependency that provides the PostgreSQL connection pool instance."""
    return db_manager.get_pool()


DbConnDep = Annotated[AsyncConnection, Depends(get_db_connection)]
DbDep = DbConnDep
PgDep = DbConnDep
DbPoolDep = Annotated[AsyncConnectionPool, Depends(get_db_pool)]
PgPoolDep = DbPoolDep

__all__ = [
    "DbConnDep",
    "DbDep",
    "DbPoolDep",
    "PgDep",
    "PgPoolDep",
    "RedisDep",
    "get_db_connection",
    "get_db_pool",
]
