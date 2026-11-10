import json
import threading
import time
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient
from psycopg.rows import dict_row
from redis import Redis

from app.core.config import settings


def test_sse_endpoint_nonexistent_video(client: TestClient):
    fake_id = str(uuid4())
    res = client.get(f"/api/v1/videos/{fake_id}/events")
    assert res.status_code == 404


def test_sse_endpoint_ready_video_returns_completed_snapshot(client: TestClient):
    video_id = str(uuid4())
    user_id = str(uuid4())

    # Insert a ready video in DB
    with (
        psycopg.connect(str(settings.pg_dsn), row_factory=dict_row) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            """
            INSERT INTO videos (
                id, user_id, title, original_filename,
                content_type, file_size, s3_bucket, s3_key, status,
                thumbnail_url, hls_master_playlist_url, hls_status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, 'ready',
                'http://example.com/thumb.webp', 'http://example.com/master.m3u8', 'completed'
            );
            """,
            (
                video_id,
                user_id,
                "Ready SSE Video",
                "sample.mp4",
                "video/mp4",
                1024,
                settings.s3_bucket,
                f"raw/{user_id}/{video_id}/sample.mp4",
            ),
        )

    # Connect to SSE endpoint
    with client.stream("GET", f"/api/v1/videos/{video_id}/events") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        lines = [line for line in response.iter_lines() if line.startswith("data: ")]
        assert len(lines) >= 1

        payload = json.loads(lines[0].replace("data: ", ""))
        assert payload["status"] == "ready"
        assert payload["progress"] == 100.0
        assert payload["event_type"] == "video.vod.completed"


def test_sse_endpoint_processing_video_streams_events(client: TestClient):
    video_id = str(uuid4())
    user_id = str(uuid4())

    # Insert an uploaded/processing video in DB
    with (
        psycopg.connect(str(settings.pg_dsn), row_factory=dict_row) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            """
            INSERT INTO videos (
                id, user_id, title, original_filename,
                content_type, file_size, s3_bucket, s3_key, status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, 'uploaded'
            );
            """,
            (
                video_id,
                user_id,
                "Processing SSE Video",
                "sample.mp4",
                "video/mp4",
                1024,
                settings.s3_bucket,
                f"raw/{user_id}/{video_id}/sample.mp4",
            ),
        )

    # Publish an event to Redis Pub/Sub in background
    r = Redis.from_url(str(settings.redis_dsn))

    def publish_terminal_event():
        time.sleep(0.3)
        ev = {
            "event_type": "video.vod.completed",
            "entity_id": video_id,
            "status": "ready",
            "step": "Published!",
            "progress": 100.0,
            "data": {"published": True},
        }
        r.publish(f"events:video:{video_id}", json.dumps(ev))

    t = threading.Thread(target=publish_terminal_event)
    t.start()

    with client.stream("GET", f"/api/v1/videos/{video_id}/events") as response:
        assert response.status_code == 200
        data_lines = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                data_lines.append(json.loads(line.replace("data: ", "")))
                if any(p.get("status") == "ready" for p in data_lines):
                    break

        t.join(timeout=2.0)
        assert len(data_lines) >= 2
        assert data_lines[0]["status"] == "uploaded"
        assert data_lines[-1]["status"] == "ready"
        assert data_lines[-1]["progress"] == 100.0
