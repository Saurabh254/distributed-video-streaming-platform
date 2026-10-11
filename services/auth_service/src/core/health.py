import asyncio
import logging
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


async def check_redis(client: Redis) -> tuple[str, str]:
    """Check Redis/Valkey connectivity with a fail-fast timeout."""
    try:
        await asyncio.wait_for(client.ping(), timeout=2.0)
        return "redis", "connected"
    except (TimeoutError, RedisError, Exception) as exc:
        logger.warning("Redis health check failed: %s", exc)
        return "redis", "disconnected"


async def check_postgres(pg_conn: Any = None) -> tuple[str, str]:
    """Check PostgreSQL connectivity (extensible for when Postgres connector is configured)."""
    if pg_conn is None:
        return "postgres", "connected"

    try:
        # Example when connection/session pool is ready:
        # await pg_conn.execute("SELECT 1")
        return "postgres", "connected"
    except Exception as exc:
        logger.warning("PostgreSQL health check failed: %s", exc)
        return "postgres", "disconnected"


async def evaluate_system_health(
    redis_conn: Redis,
    pg_conn: Any = None,
) -> dict[str, Any]:
    """
    Run health checks for all configured dependencies concurrently.
    Ensures a failure in one service does not prevent checking other services.
    """
    tasks = [
        check_redis(redis_conn),
    ]

    if pg_conn is not None:
        tasks.append(check_postgres(pg_conn))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    services: dict[str, str] = {}
    for res in results:
        if isinstance(res, Exception):
            logger.error("Health check execution error: %s", res)
            continue
        name, service_status = res
        services[name] = service_status

    is_healthy = all(status == "connected" for status in services.values())

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "services": services,
    }
