import os
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

os.environ["APP_ENV"] = "testing"
os.environ["DEBUG"] = "true"
os.environ["CATALOG_CACHE_ENABLED"] = "false"

from app.main import app


class FakeCursor:
    def __init__(self, fetchone_val=None, fetchall_val=None):
        self._fetchone_val = fetchone_val
        self._fetchall_val = fetchall_val or []
        self.last_query = None
        self.last_params = None

    async def execute(self, query: str, params: Any = None):
        self.last_query = query
        self.last_params = params

    async def fetchone(self):
        return self._fetchone_val

    async def fetchall(self):
        return self._fetchall_val

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class FakeConnection:
    def __init__(self, fetchone_val=None, fetchall_val=None):
        self.cursor_instance = FakeCursor(fetchone_val, fetchall_val)

    def cursor(self):
        return self.cursor_instance


class MockRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def setex(self, key: str, time: int, value: str):
        self.store[key] = value

    async def hget(self, name: str, key: str):
        return None

    async def ping(self):
        return True


@pytest.fixture
def mock_video_row():
    return {
        "id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "title": "Architecting Scalable Streaming Pipelines",
        "description": "Deep dive into distributed video streaming with HLS and Redis Streams.",
        "category": "Tech",
        "thumbnail_url": "http://127.0.0.1:9000/videos/thumbnails/thumb.webp",
        "duration_seconds": 724.5,
        "width": 1920,
        "height": 1080,
        "views_count": 1420,
        "likes_count": 89,
        "status": "ready",
        "hls_status": "completed",
        "created_at": "2026-10-18T20:00:00Z",
        "username": "alex_tech",
        "email": "alex@example.com",
    }


@pytest.fixture
def client():
    return TestClient(app)
