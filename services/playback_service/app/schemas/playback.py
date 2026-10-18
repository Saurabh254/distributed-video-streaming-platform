from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlaybackSessionResponse(BaseModel):
    session_id: UUID
    video_id: UUID
    title: str
    stream_type: str = "hls"  # "hls" or "mp4"
    playback_url: str
    hls_master_playlist_url: str | None = None
    qualities: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    thumbnail_url: str | None = None
    views_count: int = 0
    resume_position_seconds: float = 0.0
    status: str
    hls_status: str

    model_config = ConfigDict(from_attributes=True)


class HeartbeatRequest(BaseModel):
    session_id: UUID
    current_time: float = Field(
        ge=0.0, description="Current playhead position in seconds"
    )
    duration: float | None = Field(default=None, ge=0.0)
    is_paused: bool = False


class HeartbeatResponse(BaseModel):
    status: str = "ok"
    session_id: UUID
    current_time: float
    view_recorded: bool = False
    current_views: int


class ResumePositionResponse(BaseModel):
    video_id: UUID
    resume_position_seconds: float
    completed: bool
