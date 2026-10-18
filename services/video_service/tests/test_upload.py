import httpx
from fastapi.testclient import TestClient

from tests.conftest import create_test_token


def test_initiate_upload_unauthenticated(client: TestClient):
    payload = {
        "title": "Intro to Distributed Systems",
        "description": "Lecture 1",
        "category": "Distributed Systems",
        "filename": "lecture1.mp4",
        "content_type": "video/mp4",
        "file_size": 1024 * 1024,
    }
    response = client.post("/api/v1/videos/initiate-upload", json=payload)
    assert response.status_code == 401


def test_initiate_upload_invalid_token(client: TestClient):
    expired_token = create_test_token(expired=True)
    payload = {
        "title": "Intro to Distributed Systems",
        "filename": "lecture1.mp4",
        "content_type": "video/mp4",
        "file_size": 1024 * 1024,
    }
    response = client.post(
        "/api/v1/videos/initiate-upload",
        json=payload,
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


def test_initiate_upload_unsupported_content_type(client: TestClient):
    token = create_test_token()
    payload = {
        "title": "Document",
        "filename": "notes.pdf",
        "content_type": "application/pdf",
        "file_size": 1024,
    }
    response = client.post(
        "/api/v1/videos/initiate-upload",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "Unsupported content type" in response.json()["detail"]


def test_initiate_upload_success(client: TestClient):
    token = create_test_token()
    payload = {
        "title": "High Performance Media Pipelines",
        "description": "Deep dive into video chunking and streaming.",
        "category": "Cinema & 4K",
        "filename": "media_pipeline.mp4",
        "content_type": "video/mp4",
        "file_size": 5 * 1024 * 1024,
    }
    response = client.post(
        "/api/v1/videos/initiate-upload",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "video_id" in data
    assert "upload_url" in data
    assert "s3_key" in data
    assert data["s3_bucket"] == "videos"
    assert "X-Amz-Signature=" in data["upload_url"]
    assert "media_pipeline.mp4" in data["s3_key"]


def test_complete_without_s3_upload_fails(client: TestClient):
    token = create_test_token()
    init_res = client.post(
        "/api/v1/videos/initiate-upload",
        json={
            "title": "Missing Video",
            "filename": "missing.mp4",
            "content_type": "video/mp4",
            "file_size": 2048,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert init_res.status_code == 201
    video_id = init_res.json()["video_id"]

    # Calling complete before uploading binary to S3
    comp_res = client.post(
        f"/api/v1/videos/{video_id}/complete",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert comp_res.status_code == 400
    assert "not found in storage" in comp_res.json()["detail"]


def test_end_to_end_presigned_upload_flow(client: TestClient):
    token = create_test_token()
    user_headers = {"Authorization": f"Bearer {token}"}

    # 1. Initiate upload
    init_res = client.post(
        "/api/v1/videos/initiate-upload",
        json={
            "title": "End to End Streaming Test",
            "description": "Integration test for presigned upload",
            "category": "Live Events",
            "filename": "sample_clip.mp4",
            "content_type": "video/mp4",
            "file_size": 4096,
        },
        headers=user_headers,
    )
    assert init_res.status_code == 201
    init_data = init_res.json()
    video_id = init_data["video_id"]
    upload_url = init_data["upload_url"]

    # 2. Upload binary directly to S3 / MinIO via presigned PUT URL
    video_bytes = b"FAKEMP4DATA" * 300
    with httpx.Client() as direct_client:
        s3_res = direct_client.put(
            upload_url,
            content=video_bytes,
            headers={"Content-Type": "video/mp4"},
        )
        assert s3_res.status_code == 200

    # 3. Confirm completion
    comp_res = client.post(
        f"/api/v1/videos/{video_id}/complete",
        headers=user_headers,
    )
    assert comp_res.status_code == 200
    video_data = comp_res.json()
    assert video_data["id"] == video_id
    assert video_data["status"] == "uploaded"
    assert video_data["uploaded_at"] is not None

    # 4. Fetch video status
    get_res = client.get(
        f"/api/v1/videos/{video_id}",
        headers=user_headers,
    )
    assert get_res.status_code == 200
    assert get_res.json()["id"] == video_id

    # 5. List user videos
    list_res = client.get(
        "/api/v1/videos",
        headers=user_headers,
    )
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(v["id"] == video_id for v in list_data["items"])
