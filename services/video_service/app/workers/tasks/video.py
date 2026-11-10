import asyncio
import logging
import os
import shutil
import tempfile
from typing import Any

from botocore.client import Config
import boto3

from app.core.config import settings
from app.core.connectors.postgres import db_manager
from app.core.events.publisher import event_publisher
from app.repository.video import VideoRepository
from app.schemas.events import EventStatus, VideoEventType
from app.workers.base_task import BaseTask
from app.workers.celery_app import app
from app.workers.hls_processor import transcode_to_hls
from app.workers.image_processor import (
    extract_frame_ffmpeg,
    extract_video_metadata,
    generate_responsive_thumbnails,
)

logger = logging.getLogger(__name__)


def _get_s3_client():
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


class VideoTask(BaseTask):
    abstract = True


@app.task(bind=True, base=VideoTask, queue="video-processing")
def process_video(self, video_id: str) -> dict[str, Any]:
    """
    VOD Video Processing Celery Task.
    Downloads the uploaded raw video from S3, extracts video metadata,
    generates responsive thumbnails, transcodes adaptive bitrate HLS streams,
    uploads processed assets back to S3, updates the database, and emits real-time events.
    """

    async def _runner() -> dict[str, Any]:
        async with db_manager.get_connection() as db:
            repo = VideoRepository(db)
            video = await repo.get_video_by_id(video_id)
            if not video:
                raise ValueError(f"Video {video_id} not found")

            # 1. Update status to processing
            await repo.update_all_results(
                video_id=video_id,
                status="processing",
                hls_status="processing",
            )

        # Stage 1: Pipeline Initialized (0%)
        event_publisher.publish_vod_event(
            video_id=video_id,
            event_type=VideoEventType.VOD_PROCESSING_STARTED,
            status=EventStatus.PROCESSING,
            step="Initializing media processing pipeline...",
            progress=0.0,
            data={"status": "processing"},
        )

        s3_bucket = video["s3_bucket"]
        s3_key = video["s3_key"]
        s3 = _get_s3_client()

        work_dir = tempfile.mkdtemp(prefix=f"video_{video_id}_")
        raw_video_path = os.path.join(work_dir, "source.mp4")

        try:
            # Stage 2: Download raw video from S3
            logger.info("Downloading raw video %s from S3 bucket %s key %s", video_id, s3_bucket, s3_key)
            await asyncio.to_thread(s3.download_file, s3_bucket, s3_key, raw_video_path)

            # Stage 3: Probing Codecs & Metadata (20%)
            logger.info("Probing video metadata for %s", video_id)
            meta = await asyncio.to_thread(extract_video_metadata, raw_video_path)
            width = meta.get("width")
            height = meta.get("height")
            duration = meta.get("duration", 0.0)
            codec = meta.get("codec")

            event_publisher.publish_vod_event(
                video_id=video_id,
                event_type=VideoEventType.VOD_PROBING,
                status=EventStatus.PROCESSING,
                step="Probing video codecs & metadata...",
                progress=20.0,
                data={
                    "duration": duration,
                    "resolution": f"{width}x{height}" if width and height else None,
                    "codec": codec,
                },
            )

            # Stage 4: Extracting Thumbnails (45%)
            event_publisher.publish_vod_event(
                video_id=video_id,
                event_type=VideoEventType.VOD_THUMBNAIL_GENERATING,
                status=EventStatus.PROCESSING,
                step="Extracting keyframes & generating responsive thumbnails...",
                progress=45.0,
            )

            sample_frame_path = os.path.join(work_dir, "frame.png")
            timestamp = min(1.0, duration / 2.0) if duration > 0 else 0.5
            extracted = await asyncio.to_thread(
                extract_frame_ffmpeg, raw_video_path, sample_frame_path, timestamp
            )

            thumbs_dir = os.path.join(work_dir, "thumbnails")
            thumb_urls: dict[str, str] = {}
            primary_thumb_url: str | None = None

            if extracted:
                generated_thumbs = await asyncio.to_thread(
                    generate_responsive_thumbnails, sample_frame_path, thumbs_dir
                )
                for variant, file_path in generated_thumbs.items():
                    ext = os.path.splitext(file_path)[1].lstrip(".")
                    ct = "image/webp" if ext == "webp" else "image/jpeg"
                    s3_thumb_key = f"thumbnails/{video_id}/{variant}.{ext}"
                    await asyncio.to_thread(
                        s3.upload_file,
                        file_path,
                        s3_bucket,
                        s3_thumb_key,
                        ExtraArgs={"ContentType": ct},
                    )
                    url = f"{settings.s3_public_endpoint_url}/{s3_bucket}/{s3_thumb_key}"
                    thumb_urls[variant] = url

                primary_thumb_url = thumb_urls.get("large") or thumb_urls.get("poster")
            else:
                logger.warning("Frame extraction failed for video %s", video_id)

            # Stage 5: Thumbnails Ready (55%)
            event_publisher.publish_vod_event(
                video_id=video_id,
                event_type=VideoEventType.VOD_THUMBNAIL_READY,
                status=EventStatus.PROCESSING,
                step="Thumbnails generated & uploaded to storage",
                progress=55.0,
                data={"thumbnail_url": primary_thumb_url, "thumbnails": thumb_urls},
            )

            # Stage 6: Transcoding ABR variants to HLS (70%)
            event_publisher.publish_vod_event(
                video_id=video_id,
                event_type=VideoEventType.VOD_TRANSCODING_STARTED,
                status=EventStatus.PROCESSING,
                step="Transcoding adaptive bitrate variants (HLS)...",
                progress=70.0,
            )

            hls_dir = os.path.join(work_dir, "hls")
            hls_info = await asyncio.to_thread(
                transcode_to_hls,
                video_path=raw_video_path,
                output_dir=hls_dir,
                source_height=height,
                segment_duration=4,
            )

            # Stage 7: Uploading HLS chunks & playlists (85%)
            event_publisher.publish_vod_event(
                video_id=video_id,
                event_type=VideoEventType.VOD_TRANSCODING_PROGRESS,
                status=EventStatus.PROCESSING,
                step="Uploading HLS media chunks & playlist manifests...",
                progress=85.0,
                data={"variants": hls_info["variants"]},
            )

            for rel_path, abs_path in hls_info["all_files"]:
                s3_hls_key = f"hls/{video_id}/{rel_path}"
                content_type = (
                    "application/vnd.apple.mpegurl"
                    if rel_path.endswith(".m3u8")
                    else "video/MP2T"
                )
                await asyncio.to_thread(
                    s3.upload_file,
                    abs_path,
                    s3_bucket,
                    s3_hls_key,
                    ExtraArgs={"ContentType": content_type},
                )

            # Stage 8: Master Playlist Ready (95%)
            master_playlist_url = (
                f"{settings.s3_public_endpoint_url}/{s3_bucket}/hls/{video_id}/master.m3u8"
            )
            event_publisher.publish_vod_event(
                video_id=video_id,
                event_type=VideoEventType.VOD_HLS_READY,
                status=EventStatus.PROCESSING,
                step="Master playlist indexed & verified",
                progress=95.0,
                data={"hls_master_playlist_url": master_playlist_url},
            )

            # Stage 9: Completed & Published (100%)
            async with db_manager.get_connection() as db:
                repo = VideoRepository(db)
                await repo.update_all_results(
                    video_id=video_id,
                    status="ready",
                    thumbnail_url=primary_thumb_url,
                    duration_seconds=duration,
                    width=width,
                    height=height,
                    hls_status="completed",
                    hls_master_playlist_url=master_playlist_url,
                )

            event_publisher.publish_vod_event(
                video_id=video_id,
                event_type=VideoEventType.VOD_COMPLETED,
                status=EventStatus.READY,
                step="Published & ready for streaming!",
                progress=100.0,
                data={
                    "status": "ready",
                    "published": True,
                    "thumbnail_url": primary_thumb_url,
                    "hls_master_playlist_url": master_playlist_url,
                    "duration": duration,
                    "width": width,
                    "height": height,
                },
                flush_immediately=True,
            )

            logger.info("Video %s processing completed successfully", video_id)
            return {
                "video_id": video_id,
                "status": "ready",
                "thumbnail_url": primary_thumb_url,
                "hls_master_playlist_url": master_playlist_url,
                "duration": duration,
                "width": width,
                "height": height,
            }

        except Exception as exc:
            logger.exception("Failed to process video %s: %s", video_id, exc)
            async with db_manager.get_connection() as db:
                repo = VideoRepository(db)
                await repo.update_all_results(
                    video_id=video_id,
                    status="failed",
                    hls_status="failed",
                )
            event_publisher.publish_vod_event(
                video_id=video_id,
                event_type=VideoEventType.VOD_FAILED,
                status=EventStatus.FAILED,
                step=f"Processing failed: {str(exc)}",
                progress=100.0,
                data={"error": str(exc)},
                flush_immediately=True,
            )
            raise
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    return asyncio.run(_runner())
