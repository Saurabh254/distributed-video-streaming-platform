from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VideoUploadInitiateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Video title")
    description: str | None = Field(
        default=None, max_length=2000, description="Video description"
    )
    category: str | None = Field(
        default=None, max_length=100, description="Video category"
    )
    filename: str = Field(
        ..., min_length=1, max_length=255, description="Original filename"
    )
    content_type: str = Field(..., description="MIME content type (e.g. video/mp4)")
    file_size: int = Field(..., gt=0, description="Video file size in bytes")


class VideoUploadInitiateResponse(BaseModel):
    video_id: str
    upload_url: str
    s3_key: str
    s3_bucket: str
    expires_in: int


class VideoUploadCompleteRequest(BaseModel):
    client_duration_seconds: float | None = Field(
        default=None,
        ge=0,
        description="Optional client-detected video duration in seconds",
    )


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | str
    user_id: UUID | str
    title: str
    description: str | None = None
    category: str | None = None
    original_filename: str
    content_type: str
    file_size: int
    s3_bucket: str
    s3_key: str
    status: str
    thumbnail_url: str | None = None
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    hls_master_playlist_url: str | None = None
    hls_status: str | None = "pending"
    created_at: datetime
    updated_at: datetime
    uploaded_at: datetime | None = None


class VideoListResponse(BaseModel):
    items: list[VideoResponse]
    total: int
    limit: int
    offset: int
