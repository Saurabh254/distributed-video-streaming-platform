import logging

from redis.asyncio import Redis
from redis.exceptions import (
    ConnectionError as RedisConnectionError,
)
from redis.exceptions import (
    TimeoutError as RedisTimeoutError,
)
from src.core.config import settings
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class RedisManager:
    def __init__(self, max_connections: int = 50) -> None:
        self._client: Redis | None = None
        self._max_connections = max_connections

    async def start(self) -> None:
        if self._client is not None:
            return

        client = Redis.from_url(
            str(settings.redis_dsn),
            decode_responses=True,
            max_connections=self._max_connections,
            socket_connect_timeout=3,
            socket_timeout=5,
            health_check_interval=30,
        )

        try:
            await self.validate_connection(client)
        except BaseException:
            await client.aclose()
            raise

        self._client = client
        logger.info("Connected to Redis/Valkey")

    @retry(
        retry=retry_if_exception_type((RedisConnectionError, RedisTimeoutError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def validate_connection(self, client: Redis) -> bool:
        await client.ping()
        return True

    def get_client(self) -> Redis:
        if self._client is None:
            raise RuntimeError("Redis has not been initialized")

        return self._client

    async def close(self) -> None:
        client = self._client
        self._client = None

        if client is not None:
            await client.aclose()
            logger.info("Redis connection pool closed")


redis_manager = RedisManager()
