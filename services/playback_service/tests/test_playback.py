import uuid

from fastapi.testclient import TestClient

from app.core.dependencies import get_db_connection, get_redis, get_s3
from app.main import app
from tests.conftest import FakeConnection, MockRedis, MockS3Manager


def test_initiate_playback_hls(mock_playable_video):
    vid_id = mock_playable_video["id"]
    fake_conn = FakeConnection(fetchone_val=mock_playable_video)
    mock_redis = MockRedis()
    mock_s3 = MockS3Manager()

    app.dependency_overrides[get_db_connection] = lambda: fake_conn
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_s3] = lambda: mock_s3

    with TestClient(app) as client:
        res = client.get(f"/api/v1/playback/{vid_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["video_id"] == str(vid_id)
        assert data["stream_type"] == "hls"
        assert data["playback_url"] == mock_playable_video["hls_master_playlist_url"]
        assert "1080p" in data["qualities"]
        assert "720p" in data["qualities"]
        assert "session_id" in data

    app.dependency_overrides.clear()


def test_initiate_playback_mp4_fallback(mock_playable_video):
    # Simulate video uploaded but HLS still processing
    mock_playable_video["hls_status"] = "processing"
    mock_playable_video["hls_master_playlist_url"] = None

    vid_id = mock_playable_video["id"]
    fake_conn = FakeConnection(fetchone_val=mock_playable_video)
    mock_redis = MockRedis()
    mock_s3 = MockS3Manager()

    app.dependency_overrides[get_db_connection] = lambda: fake_conn
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_s3] = lambda: mock_s3

    with TestClient(app) as client:
        res = client.get(f"/api/v1/playback/{vid_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["stream_type"] == "mp4"
        assert "mock_sig" in data["playback_url"]

    app.dependency_overrides.clear()


def test_initiate_playback_not_found():
    fake_conn = FakeConnection(fetchone_val=None)
    mock_redis = MockRedis()
    mock_s3 = MockS3Manager()

    app.dependency_overrides[get_db_connection] = lambda: fake_conn
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_s3] = lambda: mock_s3

    random_id = str(uuid.uuid4())
    with TestClient(app) as client:
        res = client.get(f"/api/v1/playback/{random_id}")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    app.dependency_overrides.clear()


def test_initiate_playback_pending_upload(mock_playable_video):
    mock_playable_video["status"] = "pending_upload"
    vid_id = mock_playable_video["id"]

    fake_conn = FakeConnection(fetchone_val=mock_playable_video)
    mock_redis = MockRedis()
    mock_s3 = MockS3Manager()

    app.dependency_overrides[get_db_connection] = lambda: fake_conn
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_s3] = lambda: mock_s3

    with TestClient(app) as client:
        res = client.get(f"/api/v1/playback/{vid_id}")
        assert res.status_code == 400
        assert "not been completed" in res.json()["detail"]

    app.dependency_overrides.clear()


def test_heartbeat_records_view_at_threshold(mock_playable_video):
    vid_id = mock_playable_video["id"]
    session_id = uuid.uuid4()

    fake_conn = FakeConnection(fetchone_val={"views_count": 51})
    mock_redis = MockRedis()
    mock_s3 = MockS3Manager()

    # Pre-populate session in Redis
    mock_redis.store[f"session:{session_id}"] = {
        "video_id": str(vid_id),
        "user_id": "",
        "view_counted": "0",
    }

    app.dependency_overrides[get_db_connection] = lambda: fake_conn
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_s3] = lambda: mock_s3

    with TestClient(app) as client:
        # Step 1: Heartbeat at 2 seconds (below 5s threshold) -> no view recorded
        res1 = client.post(
            f"/api/v1/playback/{vid_id}/heartbeat",
            json={
                "session_id": str(session_id),
                "current_time": 2.0,
                "duration": 185.0,
                "is_paused": False,
            },
        )
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["view_recorded"] is False

        # Step 2: Heartbeat at 5.5 seconds (crosses threshold) -> view recorded
        res2 = client.post(
            f"/api/v1/playback/{vid_id}/heartbeat",
            json={
                "session_id": str(session_id),
                "current_time": 5.5,
                "duration": 185.0,
                "is_paused": False,
            },
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["view_recorded"] is True
        assert data2["current_views"] == 1

        # Step 3: Subsequent heartbeat in same session does not duplicate view count
        res3 = client.post(
            f"/api/v1/playback/{vid_id}/heartbeat",
            json={
                "session_id": str(session_id),
                "current_time": 10.0,
                "duration": 185.0,
                "is_paused": False,
            },
        )
        assert res3.status_code == 200
        data3 = res3.json()
        assert data3["view_recorded"] is False

    app.dependency_overrides.clear()


def test_resume_position_unauthenticated():
    random_id = str(uuid.uuid4())
    with TestClient(app) as client:
        res = client.get(f"/api/v1/playback/{random_id}/resume")
        assert res.status_code == 200
        data = res.json()
        assert data["resume_position_seconds"] == 0.0
        assert data["completed"] is False
