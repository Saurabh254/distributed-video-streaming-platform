import os
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

os.environ["APP_ENV"] = "testing"
os.environ["DEBUG"] = "true"

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
        self.counters = {}

    async def hset(self, key: str, field_or_mapping=None, value=None, mapping=None):
        if key not in self.store:
            self.store[key] = {}
        if mapping:
            self.store[key].update(mapping)
        elif field_or_mapping and value is not None:
            self.store[key][field_or_mapping] = str(value)

    async def hget(self, key: str, field: str):
        return self.store.get(key, {}).get(field)

    async def hgetall(self, key: str):
        return self.store.get(key, {})

    async def hincrby(self, key: str, field: str, amount: int = 1):
        if key not in self.store:
            self.store[key] = {}
        curr = int(self.store[key].get(field, 0))
        new_val = curr + amount
        self.store[key][field] = str(new_val)
        return new_val

    async def expire(self, key: str, time: int):
        return True

    async def ping(self):
        return True


class MockS3Manager:
    def generate_presigned_get_url(self, bucket: str, key: str, expires_in: int = 3600):
        return f"http://127.0.0.1:9000/{bucket}/{key}?signature=mock_sig"

    async def head_object(self, bucket: str, key: str):
        return {"ContentLength": 1024}

    async def validate_connection(self):
        return True


@pytest.fixture
def mock_playable_video():
    vid_id = uuid.uuid4()
    return {
        "id": vid_id,
        "user_id": uuid.uuid4(),
        "title": "Introduction to Distributed Video Streaming",
        "description": "Learn HLS and adaptive bitrate streaming.",
        "s3_bucket": "videos",
        "s3_key": f"raw/{vid_id}/video.mp4",
        "status": "ready",
        "hls_status": "completed",
        "hls_master_playlist_url": f"http://127.0.0.1:9000/videos/hls/{vid_id}/master.m3u8",
        "duration_seconds": 185.0,
        "width": 1920,
        "height": 1080,
        "thumbnail_url": f"http://127.0.0.1:9000/videos/thumbnails/{vid_id}/large.webp",
        "views_count": 50,
    }


@pytest.fixture
def client():
    return TestClient(app)
