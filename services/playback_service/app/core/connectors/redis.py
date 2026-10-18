import logging

from redis.asyncio import Redis
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisManager:
    """Manages Redis connection lifecycle for telemetry, sessions, and view counters."""

    def __init__(self) -> None:
        self._client: Redis | None = None

    async def start(self) -> None:
        """Initialize Redis connection and verify ping."""
        if self._client is not None:
            return

        self._client = Redis.from_url(
            str(settings.redis_dsn),
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
        )
        await self.validate_connection()
        logger.info("Redis client connected (%s)", settings.redis_dsn)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("Redis client closed")

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def validate_connection(self) -> bool:
        """Validate connection by sending PING."""
        if self._client is None:
            raise RuntimeError("Redis client not initialized")
        pong = await self._client.ping()
        if not pong:
            raise RuntimeError("Redis ping failed")
        return True

    def get_client(self) -> Redis:
        if self._client is None:
            raise RuntimeError("Redis client has not been initialized")
        return self._client


redis_manager = RedisManager()
