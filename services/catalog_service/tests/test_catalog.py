import uuid

from fastapi.testclient import TestClient

from app.core.dependencies import get_db_connection, get_redis
from app.main import app
from tests.conftest import FakeConnection, MockRedis


def test_list_videos(mock_video_row):
    fake_conn = FakeConnection(
        fetchone_val={"total": 1},
        fetchall_val=[mock_video_row],
    )
    mock_redis = MockRedis()

    app.dependency_overrides[get_db_connection] = lambda: fake_conn
    app.dependency_overrides[get_redis] = lambda: mock_redis

    with TestClient(app) as client:
        res = client.get("/api/v1/catalog/videos")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        video = data["items"][0]
        assert video["id"] == mock_video_row["id"]
        assert video["title"] == mock_video_row["title"]
        assert video["channel"]["name"] == "alex_tech"
        assert video["channel"]["handle"] == "@alex_tech"
        assert video["resolution"] == "1080p"
        assert video["duration"] == "12:04"

    app.dependency_overrides.clear()


def test_list_videos_with_category_and_search(mock_video_row):
    fake_conn = FakeConnection(
        fetchone_val={"total": 1},
        fetchall_val=[mock_video_row],
    )
    mock_redis = MockRedis()

    app.dependency_overrides[get_db_connection] = lambda: fake_conn
    app.dependency_overrides[get_redis] = lambda: mock_redis

    with TestClient(app) as client:
        res = client.get(
            "/api/v1/catalog/videos?category=Tech&q=Scalable&sort=views&limit=10&offset=0"
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    app.dependency_overrides.clear()


def test_get_video_detail_success(mock_video_row):
    vid_id = mock_video_row["id"]
    fake_conn = FakeConnection(
        fetchone_val=mock_video_row,
        fetchall_val=[],
    )
    mock_redis = MockRedis()

    app.dependency_overrides[get_db_connection] = lambda: fake_conn
    app.dependency_overrides[get_redis] = lambda: mock_redis

    with TestClient(app) as client:
        res = client.get(f"/api/v1/catalog/videos/{vid_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["video"]["id"] == vid_id
        assert data["video"]["title"] == mock_video_row["title"]
        assert isinstance(data["related_videos"], list)

    app.dependency_overrides.clear()


def test_get_video_detail_not_found():
    fake_conn = FakeConnection(fetchone_val=None, fetchall_val=[])
    mock_redis = MockRedis()

    app.dependency_overrides[get_db_connection] = lambda: fake_conn
    app.dependency_overrides[get_redis] = lambda: mock_redis

    random_id = str(uuid.uuid4())
    with TestClient(app) as client:
        res = client.get(f"/api/v1/catalog/videos/{random_id}")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    app.dependency_overrides.clear()


def test_list_categories():
    fake_conn = FakeConnection(
        fetchall_val=[
            {"name": "Tech", "video_count": 5},
            {"name": "Design", "video_count": 3},
        ]
    )
    mock_redis = MockRedis()

    app.dependency_overrides[get_db_connection] = lambda: fake_conn
    app.dependency_overrides[get_redis] = lambda: mock_redis

    with TestClient(app) as client:
        res = client.get("/api/v1/catalog/categories")
        assert res.status_code == 200
        data = res.json()
        assert len(data["categories"]) == 2
        assert data["categories"][0]["name"] == "Tech"
        assert data["categories"][0]["video_count"] == 5

    app.dependency_overrides.clear()
