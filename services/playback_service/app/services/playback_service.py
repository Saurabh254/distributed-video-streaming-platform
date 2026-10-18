import logging
import uuid
from uuid import UUID

from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.core.config import settings
from app.core.connectors.s3 import S3Manager
from app.repository.playback import PlaybackRepository
from app.schemas.playback import (
    HeartbeatRequest,
    HeartbeatResponse,
    PlaybackSessionResponse,
    ResumePositionResponse,
)

logger = logging.getLogger(__name__)


class PlaybackService:
    """Coordinates video streaming sessions, ABR manifests, telemetry, and view counting."""

    def __init__(
        self,
        repo: PlaybackRepository,
        redis: Redis,
        s3: S3Manager,
    ) -> None:
        self._repo = repo
        self._redis = redis
        self._s3 = s3

    def _determine_qualities(self, height: int | None) -> list[str]:
        """Determine available ABR variants according to transcoded heights."""
        h = height or 1080
        qualities = []
        if h >= 1080:
            qualities.append("1080p")
        if h >= 720:
            qualities.append("720p")
        if h >= 480:
            qualities.append("480p")
        qualities.append("360p")
        return qualities

    async def get_live_views(self, video_id: str, db_views: int) -> int:
        """Fetch realtime view count combining Redis and database."""
        try:
            cached = await self._redis.hget(f"video:stats:{video_id}", "views")
            if cached is not None:
                return max(db_views, int(cached))
        except Exception as e:
            logger.debug("Failed to read views from Redis: %s", e)
        return db_views

    async def initiate_playback(
        self,
        video_id: UUID | str,
        user_id: str | None = None,
    ) -> PlaybackSessionResponse:
        """Initialize streaming session and resolve HLS master playlist."""
        video = await self._repo.get_video(video_id)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video '{video_id}' not found",
            )

        if video["status"] == "pending_upload":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Video upload has not been completed yet",
            )

        vid_str = str(video["id"])
        hls_ready = (
            video.get("hls_status") == "completed"
            and video.get("hls_master_playlist_url") is not None
        )

        if hls_ready:
            stream_type = "hls"
            playback_url = video["hls_master_playlist_url"]
            qualities = self._determine_qualities(video.get("height"))
        else:
            # Fallback to direct S3 or presigned raw video while HLS is processing
            stream_type = "mp4"
            bucket = video["s3_bucket"]
            key = video["s3_key"]
            playback_url = self._s3.generate_presigned_get_url(
                bucket=bucket,
                key=key,
                expires_in=settings.session_expiry_seconds,
            )
            qualities = ["Original"]

        # Check for user resume position
        resume_pos = 0.0
        if user_id:
            history = await self._repo.get_resume_position(user_id, vid_str)
            if history and not history.get("completed"):
                resume_pos = float(history.get("last_position_seconds") or 0.0)

        # Generate unique session
        session_id = uuid.uuid4()
        session_key = f"session:{session_id}"
        await self._redis.hset(
            session_key,
            mapping={
                "video_id": vid_str,
                "user_id": user_id or "",
                "view_counted": "0",
            },
        )
        await self._redis.expire(session_key, settings.session_expiry_seconds)

        live_views = await self.get_live_views(vid_str, int(video["views_count"]))

        return PlaybackSessionResponse(
            session_id=session_id,
            video_id=video["id"],
            title=video["title"],
            stream_type=stream_type,
            playback_url=playback_url,
            hls_master_playlist_url=video.get("hls_master_playlist_url"),
            qualities=qualities,
            duration_seconds=float(video.get("duration_seconds") or 0.0),
            thumbnail_url=video.get("thumbnail_url"),
            views_count=live_views,
            resume_position_seconds=resume_pos,
            status=video["status"],
            hls_status=video.get("hls_status", "pending"),
        )

    async def record_heartbeat(
        self,
        video_id: UUID | str,
        req: HeartbeatRequest,
        user_id: str | None = None,
    ) -> HeartbeatResponse:
        """Process heartbeat to update playhead position and record views."""
        vid_str = str(video_id)
        session_key = f"session:{req.session_id}"

        session_data = await self._redis.hgetall(session_key)
        view_recorded = False

        if session_data:
            view_counted = session_data.get("view_counted") == "1"

            # Check if threshold crossed
            if (
                not view_counted
                and req.current_time >= settings.view_count_threshold_seconds
            ):
                # Atomically mark session view counted
                await self._redis.hset(session_key, "view_counted", "1")
                # Increment Redis counter
                new_views = await self._redis.hincrby(
                    f"video:stats:{vid_str}", "views", 1
                )
                # Persist to database
                await self._repo.increment_views(vid_str)
                view_recorded = True
                logger.info(
                    "Recorded view for video %s (total views: %d)",
                    vid_str,
                    new_views,
                )

        # Update watch progress for authenticated user
        effective_user_id = user_id or (
            session_data.get("user_id") if session_data else None
        )
        if effective_user_id and effective_user_id != "":
            duration = req.duration or 0.0
            completed = duration > 0 and req.current_time >= (duration - 5.0)
            await self._repo.upsert_playback_history(
                user_id=effective_user_id,
                video_id=vid_str,
                session_id=req.session_id,
                position_seconds=req.current_time,
                duration_seconds=duration,
                completed=completed,
            )

        current_views = await self.get_live_views(vid_str, 0)

        return HeartbeatResponse(
            status="ok",
            session_id=req.session_id,
            current_time=req.current_time,
            view_recorded=view_recorded,
            current_views=current_views,
        )

    async def get_resume_position(
        self,
        video_id: UUID | str,
        user_id: str,
    ) -> ResumePositionResponse:
        """Retrieve last saved playhead position for user."""
        row = await self._repo.get_resume_position(user_id, video_id)
        if not row:
            return ResumePositionResponse(
                video_id=UUID(str(video_id)),
                resume_position_seconds=0.0,
                completed=False,
            )
        return ResumePositionResponse(
            video_id=UUID(str(video_id)),
            resume_position_seconds=float(row.get("last_position_seconds") or 0.0),
            completed=bool(row.get("completed")),
        )
