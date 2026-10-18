import json
import logging
import re
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.core.config import settings
from app.core.connectors.s3 import S3Manager
from app.repository.video import VideoRepository
from app.schemas.video import (
    VideoListResponse,
    VideoResponse,
    VideoUploadCompleteRequest,
    VideoUploadInitiateRequest,
    VideoUploadInitiateResponse,
)

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and strange characters."""
    clean = re.sub(r"[^\w\.-]", "_", filename.strip())
    return clean or "video.mp4"


class UploadService:
    def __init__(
        self,
        repo: VideoRepository,
        s3: S3Manager,
        redis: Redis,
    ) -> None:
        self.repo = repo
        self.s3 = s3
        self.redis = redis

    async def initiate_upload(
        self,
        user_id: str | UUID,
        req: VideoUploadInitiateRequest,
    ) -> VideoUploadInitiateResponse:
        # 1. Validate content type
        if req.content_type.lower() not in [
            ct.lower() for ct in settings.allowed_content_types
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unsupported content type '{req.content_type}'. "
                    f"Allowed types: {', '.join(settings.allowed_content_types)}"
                ),
            )

        # 2. Validate file size
        if req.file_size > settings.max_upload_size_bytes:
            max_mb = settings.max_upload_size_bytes // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed limit of {max_mb} MB",
            )

        # 3. Generate unique identifiers and S3 key
        video_id = uuid4()
        safe_filename = sanitize_filename(req.filename)
        s3_key = f"raw/{user_id}/{video_id}/{safe_filename}"
        bucket = settings.s3_bucket

        # 4. Insert video record in DB with pending_upload status
        video_record = await self.repo.create_video(
            video_id=video_id,
            user_id=user_id,
            title=req.title,
            description=req.description,
            category=req.category,
            original_filename=req.filename,
            content_type=req.content_type,
            file_size=req.file_size,
            s3_bucket=bucket,
            s3_key=s3_key,
            status="pending_upload",
        )

        # 5. Generate S3 presigned PUT URL
        try:
            presigned_url = self.s3.generate_presigned_put_url(
                bucket=bucket,
                key=s3_key,
                content_type=req.content_type,
                expires_in=settings.s3_presigned_expiry_seconds,
            )
        except Exception as exc:
            logger.exception("Failed to generate presigned PUT URL")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate upload URL",
            ) from exc

        logger.info(
            "Initiated video upload: video_id=%s, user_id=%s, key=%s",
            video_id,
            user_id,
            s3_key,
        )

        return VideoUploadInitiateResponse(
            video_id=str(video_record["id"]),
            upload_url=presigned_url,
            s3_key=s3_key,
            s3_bucket=bucket,
            expires_in=settings.s3_presigned_expiry_seconds,
        )

    async def complete_upload(
        self,
        video_id: str | UUID,
        user_id: str | UUID,
        req: VideoUploadCompleteRequest | None = None,
    ) -> VideoResponse:
        # 1. Fetch video record
        video = await self.repo.get_video_by_id(video_id)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found",
            )

        # 2. Check ownership
        if str(video["user_id"]) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to complete this upload",
            )

        # 3. If already uploaded or processed, return idempotently
        if video["status"] in ("uploaded", "processing", "ready"):
            return VideoResponse.model_validate(video)

        # 4. Verify object presence in S3 / MinIO
        s3_meta = await self.s3.head_object(
            bucket=video["s3_bucket"],
            key=video["s3_key"],
        )
        if not s3_meta:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded object was not found in storage. Ensure upload completed successfully.",
            )

        # 5. Update status to uploaded
        now = datetime.now(UTC)
        updated_video = await self.repo.update_status(
            video_id=video_id,
            status="uploaded",
            uploaded_at=now,
        )
        if not updated_video:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update video status",
            )

        # 6. Publish event to Redis Stream for guaranteed pipeline consumption
        try:
            stream_payload = {
                "event": "video.uploaded",
                "video_id": str(video_id),
                "user_id": str(user_id),
                "s3_bucket": video["s3_bucket"],
                "s3_key": video["s3_key"],
                "content_type": video["content_type"],
                "file_size": str(s3_meta.get("ContentLength", video["file_size"])),
                "timestamp": now.isoformat(),
            }
            await self.redis.xadd("stream:video:events", stream_payload)

            # Also publish to PubSub channel for real-time subscribers
            await self.redis.publish(
                "events:video:uploaded", json.dumps(stream_payload)
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to publish video.uploaded stream event to Redis: %s", exc
            )

        logger.info(
            "Video upload completed and verified: video_id=%s, size=%s",
            video_id,
            s3_meta.get("ContentLength"),
        )

        return VideoResponse.model_validate(updated_video)

    async def get_video(
        self,
        video_id: str | UUID,
        user_id: str | UUID,
    ) -> VideoResponse:
        video = await self.repo.get_video_by_id(video_id)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found",
            )

        if str(video["user_id"]) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this video",
            )

        return VideoResponse.model_validate(video)

    async def list_user_videos(
        self,
        user_id: str | UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> VideoListResponse:
        items = await self.repo.list_by_user(
            user_id=user_id, limit=limit, offset=offset
        )
        total = await self.repo.count_by_user(user_id=user_id)
        return VideoListResponse(
            items=[VideoResponse.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )
