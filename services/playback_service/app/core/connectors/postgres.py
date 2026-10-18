import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages asynchronous PostgreSQL connection pool lifecycle."""

    def __init__(self) -> None:
        self._pool: AsyncConnectionPool | None = None

    async def start(self) -> None:
        """Initialize connection pool and verify connectivity."""
        if self._pool is not None:
            return

        self._pool = AsyncConnectionPool(
            conninfo=str(settings.pg_dsn),
            min_size=settings.pg_pool_min_size,
            max_size=settings.pg_pool_max_size,
            timeout=settings.pg_pool_timeout,
            max_idle=settings.pg_pool_max_idle,
            open=False,
            kwargs={"row_factory": dict_row},
        )
        await self._pool.open()
        await self.validate_connection()
        logger.info(
            "PostgreSQL pool initialized (min=%d, max=%d)",
            settings.pg_pool_min_size,
            settings.pg_pool_max_size,
        )

    async def close(self) -> None:
        """Close connection pool gracefully."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL pool closed")

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def validate_connection(self) -> bool:
        """Execute a healthcheck query with exponential backoff."""
        async with self.get_connection() as conn, conn.cursor() as cur:
            await cur.execute("SELECT 1 AS healthy;")
            row = await cur.fetchone()
            if not row or row["healthy"] != 1:
                raise RuntimeError("PostgreSQL healthcheck failed: unexpected result")
        return True

    @asynccontextmanager
    async def get_connection(self) -> AsyncIterator[any]:
        """Acquire connection from pool and yield to caller."""
        if self._pool is None:
            raise RuntimeError("Database pool has not been initialized")
        async with self._pool.connection() as conn:
            yield conn


db_manager = DatabaseManager()
