import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import RedirectResponse

from app.core.dependencies import (
    DbConnectionDep,
    OptionalUserIdDep,
    RedisDep,
    S3Dep,
)
from app.repository.playback import PlaybackRepository
from app.schemas.playback import (
    HeartbeatRequest,
    HeartbeatResponse,
    PlaybackSessionResponse,
    ResumePositionResponse,
)
from app.services.playback_service import PlaybackService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/playback", tags=["playback"])


def get_playback_service(
    conn: DbConnectionDep,
    redis: RedisDep,
    s3: S3Dep,
) -> PlaybackService:
    repo = PlaybackRepository(conn)
    return PlaybackService(repo=repo, redis=redis, s3=s3)


@router.get(
    "/{video_id}",
    response_model=PlaybackSessionResponse,
    summary="Initiate playback session and resolve stream manifest",
)
async def initiate_playback(
    video_id: UUID,
    conn: DbConnectionDep,
    redis: RedisDep,
    s3: S3Dep,
    user_id: OptionalUserIdDep,
) -> PlaybackSessionResponse:
    """Validate video availability, generate session token, and return HLS master playlist URL."""
    service = get_playback_service(conn, redis, s3)
    return await service.initiate_playback(video_id=video_id, user_id=user_id)


@router.post(
    "/{video_id}/heartbeat",
    response_model=HeartbeatResponse,
    summary="Report player heartbeat and watch progress",
)
async def report_heartbeat(
    video_id: UUID,
    req: HeartbeatRequest,
    conn: DbConnectionDep,
    redis: RedisDep,
    s3: S3Dep,
    user_id: OptionalUserIdDep,
) -> HeartbeatResponse:
    """Update watch progress in Redis and record view count once watch threshold is reached."""
    service = get_playback_service(conn, redis, s3)
    return await service.record_heartbeat(video_id=video_id, req=req, user_id=user_id)


@router.get(
    "/{video_id}/resume",
    response_model=ResumePositionResponse,
    summary="Get user resume position",
)
async def get_resume_position(
    video_id: UUID,
    conn: DbConnectionDep,
    redis: RedisDep,
    s3: S3Dep,
    user_id: OptionalUserIdDep,
) -> ResumePositionResponse:
    """Retrieve saved playhead position for authenticated user."""
    if not user_id:
        return ResumePositionResponse(
            video_id=video_id,
            resume_position_seconds=0.0,
            completed=False,
        )
    service = get_playback_service(conn, redis, s3)
    return await service.get_resume_position(video_id=video_id, user_id=user_id)


@router.get(
    "/stream/{video_id}/master.m3u8",
    summary="HLS Master Playlist Redirect / Proxy",
)
async def get_master_playlist(
    video_id: UUID,
    conn: DbConnectionDep,
    redis: RedisDep,
    s3: S3Dep,
) -> Response:
    """Redirects client to the HLS master playlist URL."""
    repo = PlaybackRepository(conn)
    video = await repo.get_video(video_id)
    if not video or not video.get("hls_master_playlist_url"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="HLS master playlist not available for this video",
        )
    return RedirectResponse(
        url=video["hls_master_playlist_url"],
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
