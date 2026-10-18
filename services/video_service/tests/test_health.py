from fastapi.testclient import TestClient


def test_health_live(client: TestClient):
    response = client.get("/healthz/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready(client: TestClient):
    response = client.get("/healthz/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["checks"]["postgres"] == "healthy"
    assert data["checks"]["redis"] == "healthy"
    assert data["checks"]["s3"] == "healthy"
