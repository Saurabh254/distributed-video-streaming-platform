import asyncio
import logging
from typing import Any

from psycopg_pool import AsyncConnectionPool
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


async def check_redis(client: Redis) -> tuple[str, str]:
    """Check Redis/Valkey connectivity with a fail-fast timeout."""
    try:
        await asyncio.wait_for(client.ping(), timeout=2.0)
        return "redis", "connected"
    except (TimeoutError, RedisError, Exception) as exc:  # noqa: BLE001
        logger.warning("Redis health check failed: %s", exc)
        return "redis", "disconnected"


async def check_postgres(pg_conn: Any = None) -> tuple[str, str]:
    """Check PostgreSQL connectivity with a fail-fast timeout."""
    if pg_conn is None:
        return "postgres", "connected"

    try:
        if isinstance(pg_conn, AsyncConnectionPool):
            async with (
                pg_conn.connection(timeout=2.0) as conn,
                conn.cursor() as cur,
            ):
                await asyncio.wait_for(cur.execute("SELECT 1"), timeout=2.0)
        elif hasattr(pg_conn, "validate_connection"):
            await asyncio.wait_for(
                pg_conn.validate_connection(timeout=2.0), timeout=2.0
            )
        else:
            async with pg_conn.cursor() as cur:
                await asyncio.wait_for(cur.execute("SELECT 1"), timeout=2.0)
        return "postgres", "connected"
    except Exception as exc:  # noqa: BLE001
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
