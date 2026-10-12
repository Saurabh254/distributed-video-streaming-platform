import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from psycopg import AsyncConnection
from psycopg.errors import OperationalError
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool, PoolTimeout
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
    """Manages the PostgreSQL asynchronous connection pool lifecycle."""

    def __init__(
        self,
        min_size: int | None = None,
        max_size: int | None = None,
        timeout: float | None = None,
        max_idle: float | None = None,
        connection_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self._pool: AsyncConnectionPool | None = None
        self._min_size = min_size
        self._max_size = max_size
        self._timeout = timeout
        self._max_idle = max_idle
        self._connection_kwargs = connection_kwargs

    async def start(self) -> None:
        """Initialize and open the asynchronous connection pool with health validation and retry."""
        if self._pool is not None:
            return

        min_size = (
            self._min_size if self._min_size is not None else settings.pg_pool_min_size
        )
        max_size = (
            self._max_size if self._max_size is not None else settings.pg_pool_max_size
        )
        timeout = (
            self._timeout if self._timeout is not None else settings.pg_pool_timeout
        )
        max_idle = (
            self._max_idle if self._max_idle is not None else settings.pg_pool_max_idle
        )

        kwargs: dict[str, Any] = (
            {"row_factory": dict_row}
            if self._connection_kwargs is None
            else self._connection_kwargs
        )

        pool = AsyncConnectionPool(
            conninfo=str(settings.pg_dsn),
            min_size=min_size,
            max_size=max_size,
            timeout=timeout,
            max_idle=max_idle,
            check=AsyncConnectionPool.check_connection,
            kwargs=kwargs,
            open=False,
        )

        try:
            await self._open_and_validate(pool, timeout=timeout)
        except BaseException:
            await pool.close()
            raise

        self._pool = pool
        logger.info(
            "Connected to PostgreSQL connection pool (min=%d, max=%d)",
            min_size,
            max_size,
        )

    async def connect(self) -> None:
        """Alias for start() to initialize the connection pool."""
        await self.start()

    @retry(
        retry=retry_if_exception_type((OperationalError, PoolTimeout)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _open_and_validate(
        self, pool: AsyncConnectionPool, timeout: float
    ) -> None:
        await pool.open(wait=True, timeout=timeout)
        await self.validate_connection(pool, timeout=timeout)

    async def validate_connection(
        self,
        pool: AsyncConnectionPool | None = None,
        timeout: float = 2.0,
    ) -> bool:
        """Validate connection by running a ping query."""
        target_pool = pool or self._pool
        if target_pool is None:
            raise RuntimeError("PostgreSQL connection pool has not been initialized")

        async with (
            target_pool.connection(timeout=timeout) as conn,
            conn.cursor() as cur,
        ):
            await cur.execute("SELECT 1")
        return True

    async def validation_connection(self) -> bool:
        """Compatibility alias for validate_connection()."""
        return await self.validate_connection()

    def get_pool(self) -> AsyncConnectionPool:
        """Return the active connection pool instance."""
        if self._pool is None:
            raise RuntimeError("PostgreSQL connection pool has not been initialized")
        return self._pool

    @asynccontextmanager
    async def get_connection(
        self, timeout: float | None = None
    ) -> AsyncIterator[AsyncConnection]:
        """Context manager to borrow a connection from the pool and return it automatically."""
        if self._pool is None:
            raise RuntimeError("PostgreSQL connection pool has not been initialized")

        async with self._pool.connection(timeout=timeout) as conn:
            yield conn

    async def close(self) -> None:
        """Close the connection pool and release resources."""
        pool = self._pool
        self._pool = None

        if pool is not None:
            await pool.close()
            logger.info("PostgreSQL connection pool closed")


db_manager = DatabaseManager()
pg_manager = db_manager
