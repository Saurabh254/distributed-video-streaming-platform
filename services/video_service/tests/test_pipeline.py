import os
import subprocess
import tempfile
from uuid import uuid4

import boto3
import psycopg
import pytest
from botocore.client import Config
from psycopg.rows import dict_row

from app.core.config import settings
from app.workers.hls_processor import transcode_to_hls
from app.workers.image_processor import (
    extract_frame_ffmpeg,
    extract_video_metadata,
    generate_responsive_thumbnails,
)
from app.workers.tasks.video import process_video


@pytest.fixture(scope="module")
def sample_mp4_path():
    """Generate a quick 1-second synthetic MP4 clip for worker tests."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        path = f.name

    cmd = [
        "ffmpeg",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=1:size=640x360:rate=1",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        path,
        "-y",
    ]
    subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    yield path

    if os.path.exists(path):
        os.remove(path)


def test_image_processor_metadata_and_frame_extraction(sample_mp4_path):
    meta = extract_video_metadata(sample_mp4_path)
    assert meta["width"] == 640
    assert meta["height"] == 360
    assert meta["duration"] >= 0.9

    with tempfile.TemporaryDirectory() as td:
        frame_file = os.path.join(td, "frame.png")
        success = extract_frame_ffmpeg(sample_mp4_path, frame_file)
        assert success is True
        assert os.path.exists(frame_file)
        assert os.path.getsize(frame_file) > 0

        thumbs = generate_responsive_thumbnails(frame_file, os.path.join(td, "thumbs"))
        assert "large" in thumbs
        assert "medium" in thumbs
        assert "small" in thumbs
        assert "poster" in thumbs

        for file_path in thumbs.values():
            assert os.path.exists(file_path)
            assert os.path.getsize(file_path) > 0


def test_hls_transcode_processor(sample_mp4_path):
    with tempfile.TemporaryDirectory() as td:
        hls_info = transcode_to_hls(
            video_path=sample_mp4_path,
            output_dir=td,
            source_height=360,
            segment_duration=2,
        )

        assert os.path.exists(hls_info["master_playlist_path"])
        assert "360p" in hls_info["variants"]

        with open(hls_info["master_playlist_path"]) as f:
            content = f.read()
            assert "#EXTM3U" in content
            assert "360p/index.m3u8" in content

        # Verify variant playlist and segments
        variant_dir = os.path.join(td, "360p")
        assert os.path.exists(os.path.join(variant_dir, "index.m3u8"))
        ts_files = [f for f in os.listdir(variant_dir) if f.endswith(".ts")]
        assert len(ts_files) > 0


def test_celery_task_simulation_pipeline(sample_mp4_path, client):
    video_id = str(uuid4())
    user_id = str(uuid4())
    s3_bucket = settings.s3_bucket
    s3_key = f"raw/{user_id}/{video_id}/sample_test.mp4"

    # 1. Upload sample video to MinIO
    cfg = Config(signature_version="s3v4", s3={"addressing_style": "path"})
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=cfg,
    )
    with open(sample_mp4_path, "rb") as f:
        s3.put_object(
            Bucket=s3_bucket,
            Key=s3_key,
            Body=f,
            ContentType="video/mp4",
        )

    # 2. Insert video record in DB
    with (
        psycopg.connect(str(settings.pg_dsn), row_factory=dict_row) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            """
            INSERT INTO videos (
                id, user_id, title, original_filename,
                content_type, file_size, s3_bucket, s3_key, status, hls_status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, 'uploaded', 'pending'
            ) RETURNING id;
            """,
            (
                video_id,
                user_id,
                "Celery Pipeline Test Video",
                "sample_test.mp4",
                "video/mp4",
                os.path.getsize(sample_mp4_path),
                s3_bucket,
                s3_key,
            ),
        )

    # 3. Execute Celery task directly
    result = process_video(video_id=video_id)
    assert result["status"] == "ready"
    assert "master.m3u8" in result["hls_master_playlist_url"]
    assert "large.webp" in result["thumbnail_url"]

    # 4. Verify PostgreSQL database record has updated status and metadata
    with (
        psycopg.connect(str(settings.pg_dsn), row_factory=dict_row) as conn,
        conn.cursor() as cur,
    ):
        cur.execute("SELECT * FROM videos WHERE id = %s;", (video_id,))
        rec = cur.fetchone()

        assert rec["status"] == "ready"
        assert rec["hls_status"] == "completed"
        assert rec["thumbnail_url"] is not None
        assert rec["hls_master_playlist_url"] is not None
        assert rec["width"] == 640
        assert rec["height"] == 360
        assert float(rec["duration_seconds"]) >= 0.9
