from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_health_check_healthy():
    client = TestClient(app)
    with (
        patch(
            "app.api.routes.health.db_manager.validate_connection",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.api.routes.health.redis_manager.validate_connection",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.api.routes.health.s3_manager.validate_connection",
            new=AsyncMock(return_value=True),
        ),
    ):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["dependencies"]["postgres"] == "connected"
        assert data["dependencies"]["redis"] == "connected"
        assert data["dependencies"]["s3"] == "connected"


def test_health_check_unhealthy():
    client = TestClient(app)
    with (
        patch(
            "app.api.routes.health.db_manager.validate_connection",
            new=AsyncMock(side_effect=Exception("DB down")),
        ),
        patch(
            "app.api.routes.health.redis_manager.validate_connection",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.api.routes.health.s3_manager.validate_connection",
            new=AsyncMock(return_value=True),
        ),
    ):
        res = client.get("/health")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "unhealthy"
        assert data["dependencies"]["postgres"] == "unreachable"
