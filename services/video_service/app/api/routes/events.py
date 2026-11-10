import asyncio
import json
import logging
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.core.dependencies import DbDep, RedisDep
from app.repository.video import VideoRepository
from app.schemas.events import EventStatus, VideoEventType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["events"])


@router.get(
    "/{video_id}/events",
    summary="Subscribe to real-time video processing SSE stream",
    response_class=StreamingResponse,
)
async def video_events_stream(
    video_id: UUID,
    request: Request,
    db: DbDep,
    redis: RedisDep,
) -> StreamingResponse:
    """
    Server-Sent Events (SSE) streaming endpoint for VOD processing progress.
    Streams real-time pipeline events (0% -> 100% Published) to the frontend.
    """
    repo = VideoRepository(db)
    video = await repo.get_video_by_id(video_id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video {video_id} not found",
        )

    async def event_generator() -> AsyncIterator[str]:
        vid_str = str(video_id)

        # 1. Emit current database state snapshot immediately
        current_status = video.get("status", "pending_upload")
        if current_status == "ready":
            yield (
                f"data: {json.dumps({'event_type': VideoEventType.VOD_COMPLETED.value, 'entity_id': vid_str, 'status': EventStatus.READY.value, 'step': 'Published & ready for streaming!', 'progress': 100.0, 'data': {'published': True, 'thumbnail_url': video.get('thumbnail_url'), 'hls_master_playlist_url': video.get('hls_master_playlist_url')}})}\n\n"
            )
            return
        elif current_status == "failed":
            yield (
                f"data: {json.dumps({'event_type': VideoEventType.VOD_FAILED.value, 'entity_id': vid_str, 'status': EventStatus.FAILED.value, 'step': 'Processing failed', 'progress': 0.0, 'error': 'Processing error'})}\n\n"
            )
            return
        else:
            yield (
                f"data: {json.dumps({'event_type': VideoEventType.VOD_PROCESSING_STARTED.value, 'entity_id': vid_str, 'status': current_status, 'step': f'Status: {current_status}', 'progress': 0.0})}\n\n"
            )

        # 2. Subscribe to Redis Pub/Sub channel for live events
        pubsub = redis.pubsub()
        channel_name = f"events:video:{vid_str}"
        await pubsub.subscribe(channel_name)
        logger.info("Client subscribed to SSE channel: %s", channel_name)

        last_ping = asyncio.get_event_loop().time()

        try:
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    logger.info("SSE client disconnected for video: %s", vid_str)
                    break

                # Poll for messages with a short timeout
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=0.5
                )
                now = asyncio.get_event_loop().time()

                if msg is not None and msg.get("type") == "message":
                    raw_data = msg["data"]
                    yield f"data: {raw_data}\n\n"

                    # Parse message to check for terminal state
                    try:
                        payload = json.loads(raw_data)
                        ev_status = payload.get("status")
                        ev_type = payload.get("event_type")

                        if ev_status in (
                            EventStatus.READY.value,
                            EventStatus.COMPLETED.value,
                            EventStatus.FAILED.value,
                        ) or ev_type in (
                            VideoEventType.VOD_COMPLETED.value,
                            VideoEventType.VOD_FAILED.value,
                        ):
                            logger.info(
                                "Terminal event received for video %s, closing SSE stream",
                                vid_str,
                            )
                            await asyncio.sleep(0.2)
                            break
                    except Exception as parse_err:  # noqa: BLE001
                        logger.debug("SSE JSON payload parse notice: %s", parse_err)

                # Keep-alive heartbeat every 15 seconds to prevent proxy timeout
                if now - last_ping >= 15.0:
                    yield ": keep-alive\n\n"
                    last_ping = now

                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.info("SSE connection cancelled for video %s", vid_str)
        finally:
            await pubsub.unsubscribe(channel_name)
            await pubsub.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
