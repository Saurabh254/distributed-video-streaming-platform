from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from psycopg_pool import AsyncConnectionPool

from app.core.connectors.postgres import DatabaseManager
from app.core.connectors.redis import RedisManager
from app.main import app
from app.services.health_service import (
    check_postgres,
    evaluate_system_health,
)


@pytest.mark.asyncio
async def test_check_postgres_healthy():
    mgr = DatabaseManager(min_size=1, max_size=2)
    await mgr.start()
    name, status = await check_postgres(mgr.get_pool())
    assert name == "postgres"
    assert status == "connected"
    await mgr.close()


@pytest.mark.asyncio
async def test_check_postgres_none():
    name, status = await check_postgres(None)
    assert name == "postgres"
    assert status == "connected"


@pytest.mark.asyncio
async def test_check_postgres_disconnected():
    # Pass an object where connection/cursor fails
    broken_pool = AsyncMock(spec=AsyncConnectionPool)
    broken_pool.connection.side_effect = Exception("DB Connection refused")
    name, status = await check_postgres(broken_pool)
    assert name == "postgres"
    assert status == "disconnected"


@pytest.mark.asyncio
async def test_evaluate_system_health_all_healthy():
    redis_mgr = RedisManager()
    await redis_mgr.start()
    db_mgr = DatabaseManager(min_size=1, max_size=2)
    await db_mgr.start()

    report = await evaluate_system_health(
        redis_conn=redis_mgr.get_client(),
        pg_conn=db_mgr.get_pool(),
    )
    assert report["status"] == "healthy"
    assert report["services"]["redis"] == "connected"
    assert report["services"]["postgres"] == "connected"

    await db_mgr.close()
    await redis_mgr.close()


@pytest.mark.asyncio
async def test_evaluate_system_health_postgres_unhealthy():
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True

    broken_pool = AsyncMock(spec=AsyncConnectionPool)
    broken_pool.connection.side_effect = Exception("DB timeout")

    report = await evaluate_system_health(
        redis_conn=mock_redis,
        pg_conn=broken_pool,
    )
    assert report["status"] == "unhealthy"
    assert report["services"]["redis"] == "connected"
    assert report["services"]["postgres"] == "disconnected"


def test_healthz_api_endpoints():
    with TestClient(app) as client:
        # Root health endpoint
        res_root = client.get("/healthz")
        assert res_root.status_code == 200
        data_root = res_root.json()
        assert data_root["status"] == "healthy"
        assert data_root["services"]["redis"] == "connected"
        assert data_root["services"]["postgres"] == "connected"

        # /api/v1 prefix health endpoint
        res_v1 = client.get("/api/v1/healthz")
        assert res_v1.status_code == 200
        data_v1 = res_v1.json()
        assert data_v1["status"] == "healthy"
        assert data_v1["services"]["redis"] == "connected"
        assert data_v1["services"]["postgres"] == "connected"
