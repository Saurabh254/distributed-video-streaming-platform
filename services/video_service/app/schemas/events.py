from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class StreamType(str, Enum):
    VOD = "vod"
    LIVE = "live"


class EventStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoEventType(str, Enum):
    # VOD Events
    VOD_UPLOADED = "video.vod.uploaded"
    VOD_PROCESSING_STARTED = "video.vod.processing_started"
    VOD_PROBING = "video.vod.probing"
    VOD_THUMBNAIL_GENERATING = "video.vod.thumbnail_generating"
    VOD_THUMBNAIL_READY = "video.vod.thumbnail_ready"
    VOD_TRANSCODING_STARTED = "video.vod.transcoding_started"
    VOD_TRANSCODING_PROGRESS = "video.vod.transcoding_progress"
    VOD_HLS_READY = "video.vod.hls_ready"
    VOD_COMPLETED = "video.vod.completed"
    VOD_FAILED = "video.vod.failed"

    # Live Streaming Events
    LIVE_STREAM_STARTED = "video.live.started"
    LIVE_STREAM_CHUNKING = "video.live.chunking"
    LIVE_STREAM_SEGMENT_READY = "video.live.segment_ready"
    LIVE_STREAM_PLAYLIST_UPDATED = "video.live.playlist_updated"
    LIVE_STREAM_ENDED = "video.live.ended"
    LIVE_STREAM_FAILED = "video.live.failed"

    # Worker Task Lifecycle Events (BaseTask compatibility)
    TASK_STARTED = "task.started"
    TASK_RETRYING = "task.retrying"
    TASK_SUCCEEDED = "task.succeeded"
    TASK_FAILED = "task.failed"


class VideoProcessingEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    entity_id: str  # video_id (for VOD) or stream_id (for Live)
    stream_type: StreamType = StreamType.VOD
    status: EventStatus = EventStatus.PROCESSING
    step: str | None = None
    progress: float | None = None  # 0.0 to 100.0 percent
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
