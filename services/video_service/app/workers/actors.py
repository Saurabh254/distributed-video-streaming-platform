import logging
import tempfile
from pathlib import Path
from typing import Any

import boto3
import dramatiq
import psycopg
from botocore.client import Config
from psycopg.rows import dict_row
from redis import Redis

from app.core.config import settings
from app.repository.video import SyncVideoRepository
from app.workers.broker import broker  # noqa: F401 - registers broker
from app.workers.hls_processor import transcode_to_hls
from app.workers.image_processor import (
    extract_frame_ffmpeg,
    extract_video_metadata,
    generate_responsive_thumbnails,
)

logger = logging.getLogger(__name__)


def get_sync_s3_client() -> Any:
    """Initialize a synchronous boto3 S3 client for worker thread execution."""
    cfg = Config(
        signature_version="s3v4",
        s3={"addressing_style": "path"},
        retries={"max_attempts": 3, "mode": "standard"},
    )
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=cfg,
    )


@dramatiq.actor(queue_name="media_pipeline", max_retries=3)
def process_video_thumbnail(
    video_id: str, s3_bucket: str, s3_key: str
) -> dict[str, Any]:
    """
    Dramatiq background actor:
    1. Downloads video from MinIO/S3.
    2. Probes metadata (duration, width, height) via ffprobe.
    3. Extracts representative frame via ffmpeg.
    4. Generates multi-resolution WebP and JPEG thumbnails via Pillow.
    5. Uploads processed images back to MinIO under thumbnails/{video_id}/.
    6. Updates database record with thumbnail_url and metadata, transitioning status to 'ready'.
    7. Appends 'video.processed' event to Redis stream.
    """
    logger.info(
        "Starting thumbnail processing for video %s (key: %s)",
        video_id,
        s3_key,
    )

    s3 = get_sync_s3_client()

    # Step 1: Update status to 'processing' in database
    with psycopg.connect(str(settings.pg_dsn), row_factory=dict_row) as conn:
        repo = SyncVideoRepository(conn)
        repo.update_status(video_id=video_id, status="processing")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        local_video_path = str(temp_path / f"{video_id}.video")
        raw_frame_path = str(temp_path / f"{video_id}_raw_frame.png")
        thumbs_dir = str(temp_path / "thumbs")

        try:
            # Step 2: Download raw video from MinIO
            logger.info("Downloading S3 object %s/%s", s3_bucket, s3_key)
            s3.download_file(Bucket=s3_bucket, Key=s3_key, Filename=local_video_path)

            # Step 3: Extract metadata via ffprobe
            meta = extract_video_metadata(local_video_path)
            duration = meta.get("duration") or 0.0
            width = meta.get("width")
            height = meta.get("height")
            logger.info(
                "Extracted video metadata: duration=%.2fs, resolution=%sx%s",
                duration,
                width,
                height,
            )

            # Step 4: Extract representative frame via ffmpeg
            target_timestamp = min(1.0, max(0.0, duration / 2))
            extracted = extract_frame_ffmpeg(
                video_path=local_video_path,
                output_image_path=raw_frame_path,
                timestamp_sec=target_timestamp,
            )

            if not extracted:
                raise RuntimeError(
                    f"Failed to extract frame from video {video_id} at {target_timestamp}s"
                )

            # Step 5: Process responsive thumbnails with Pillow
            generated_thumbs = generate_responsive_thumbnails(
                source_image_path=raw_frame_path,
                output_dir=thumbs_dir,
            )

            # Step 6: Upload generated thumbnails to MinIO
            uploaded_keys: dict[str, str] = {}
            for variant, file_path in generated_thumbs.items():
                ext = Path(file_path).suffix.lstrip(".")
                mime_type = "image/webp" if ext == "webp" else "image/jpeg"
                dest_key = f"thumbnails/{video_id}/{variant}.{ext}"

                with open(file_path, "rb") as f:
                    s3.put_object(
                        Bucket=s3_bucket,
                        Key=dest_key,
                        Body=f,
                        ContentType=mime_type,
                    )
                uploaded_keys[variant] = dest_key
                logger.info(
                    "Uploaded thumbnail %s -> %s/%s", variant, s3_bucket, dest_key
                )

            # Construct default primary thumbnail URL
            primary_key = uploaded_keys.get("large") or uploaded_keys.get("poster")
            thumbnail_url = (
                f"{settings.s3_public_endpoint_url}/{s3_bucket}/{primary_key}"
            )

            # Step 7: Update PostgreSQL record
            with psycopg.connect(str(settings.pg_dsn), row_factory=dict_row) as conn:
                repo = SyncVideoRepository(conn)
                repo.update_processing_results(
                    video_id=video_id,
                    status="ready",
                    thumbnail_url=thumbnail_url,
                    duration_seconds=duration if duration > 0 else None,
                    width=width,
                    height=height,
                )

            # Step 8: Append video.processed event to Redis Stream
            try:
                redis = Redis.from_url(str(settings.redis_dsn), decode_responses=True)
                redis.xadd(
                    "stream:video:events",
                    {
                        "event": "video.processed",
                        "video_id": str(video_id),
                        "status": "ready",
                        "thumbnail_url": thumbnail_url,
                        "duration": str(duration),
                    },
                )
                redis.close()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to publish video.processed stream event: %s", exc
                )

            logger.info(
                "Successfully finished processing video %s -> status 'ready'",
                video_id,
            )
            return {
                "video_id": video_id,
                "status": "ready",
                "thumbnail_url": thumbnail_url,
                "thumbnails": uploaded_keys,
            }

        except Exception:
            logger.exception("Failed processing video %s", video_id)
            with psycopg.connect(str(settings.pg_dsn), row_factory=dict_row) as conn:
                repo = SyncVideoRepository(conn)
                repo.update_status(video_id=video_id, status="failed")
            raise


@dramatiq.actor(queue_name="media_pipeline", max_retries=3)
def transcode_video_hls(video_id: str, s3_bucket: str, s3_key: str) -> dict[str, Any]:
    """
    Dramatiq background actor for HLS transcoding:
    1. Updates hls_status to 'processing'.
    2. Downloads raw video from MinIO.
    3. Probes video dimensions via ffprobe.
    4. Transcodes into adaptive bitrate HLS (e.g. 720p, 480p, 360p) + master.m3u8.
    5. Uploads all playlists (.m3u8) and video segments (.ts) to MinIO under hls/{video_id}/.
    6. Updates database record with hls_master_playlist_url and hls_status='completed'.
    7. Appends 'video.hls_ready' event to Redis stream.
    """
    logger.info(
        "Starting HLS transcoding for video %s (key: %s)",
        video_id,
        s3_key,
    )

    s3 = get_sync_s3_client()

    # Step 1: Update HLS status in database
    with psycopg.connect(str(settings.pg_dsn), row_factory=dict_row) as conn:
        repo = SyncVideoRepository(conn)
        repo.update_hls_results(video_id=video_id, hls_status="processing")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        local_video_path = str(temp_path / f"{video_id}.video")
        hls_output_dir = str(temp_path / "hls")

        try:
            # Step 2: Download raw video from MinIO
            logger.info("Downloading raw video for HLS: %s/%s", s3_bucket, s3_key)
            s3.download_file(Bucket=s3_bucket, Key=s3_key, Filename=local_video_path)

            # Step 3: Probe source video height
            meta = extract_video_metadata(local_video_path)
            source_height = meta.get("height")

            # Step 4: Transcode to HLS multi-variant
            hls_info = transcode_to_hls(
                video_path=local_video_path,
                output_dir=hls_output_dir,
                source_height=source_height,
                segment_duration=4,
            )

            # Step 5: Upload all generated HLS files to MinIO
            all_files = hls_info["all_files"]
            logger.info(
                "Uploading %d HLS files to MinIO under hls/%s/",
                len(all_files),
                video_id,
            )

            for rel_path, abs_path in all_files:
                dest_key = f"hls/{video_id}/{rel_path}"
                content_type = (
                    "application/vnd.apple.mpegurl"
                    if rel_path.endswith(".m3u8")
                    else "video/MP2T"
                )
                cache_control = (
                    "no-cache"
                    if rel_path.endswith(".m3u8")
                    else "public, max-age=31536000, immutable"
                )

                with open(abs_path, "rb") as f:
                    s3.put_object(
                        Bucket=s3_bucket,
                        Key=dest_key,
                        Body=f,
                        ContentType=content_type,
                        CacheControl=cache_control,
                    )

            master_playlist_url = f"{settings.s3_public_endpoint_url}/{s3_bucket}/hls/{video_id}/master.m3u8"

            # Step 6: Update PostgreSQL database record
            with psycopg.connect(str(settings.pg_dsn), row_factory=dict_row) as conn:
                repo = SyncVideoRepository(conn)
                repo.update_hls_results(
                    video_id=video_id,
                    hls_status="completed",
                    hls_master_playlist_url=master_playlist_url,
                )

            # Step 7: Append event to Redis Stream
            try:
                redis = Redis.from_url(str(settings.redis_dsn), decode_responses=True)
                redis.xadd(
                    "stream:video:events",
                    {
                        "event": "video.hls_ready",
                        "video_id": str(video_id),
                        "hls_status": "completed",
                        "hls_url": master_playlist_url,
                        "variants": ",".join(hls_info["variants"]),
                    },
                )
                redis.close()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to publish video.hls_ready stream event: %s", exc
                )

            logger.info(
                "Successfully completed HLS transcoding for video %s: %s",
                video_id,
                master_playlist_url,
            )

            return {
                "video_id": video_id,
                "hls_status": "completed",
                "hls_master_playlist_url": master_playlist_url,
                "variants": hls_info["variants"],
            }

        except Exception:
            logger.exception("Failed HLS transcoding for video %s", video_id)
            with psycopg.connect(str(settings.pg_dsn), row_factory=dict_row) as conn:
                repo = SyncVideoRepository(conn)
                repo.update_hls_results(video_id=video_id, hls_status="failed")
            raise
