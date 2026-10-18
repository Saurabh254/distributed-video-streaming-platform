from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


def format_duration(seconds: float | None) -> str:
    """Format duration in seconds to M:SS or H:MM:SS."""
    if not seconds or seconds <= 0:
        return "0:00"
    secs = int(seconds)
    hours = secs // 3600
    minutes = (secs % 3600) // 60
    remaining_secs = secs % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{remaining_secs:02d}"
    return f"{minutes}:{remaining_secs:02d}"


class ChannelInfo(BaseModel):
    id: str
    name: str
    handle: str
    avatar: str = ""
    subscribers: str = "1.2K"
    verified: bool = False

    model_config = ConfigDict(from_attributes=True)


class VideoCatalogItem(BaseModel):
    id: str
    title: str
    description: str | None = None
    category: str = "General"
    thumbnail_url: str | None = None
    duration_seconds: float = 0.0
    duration: str = "0:00"
    width: int | None = None
    height: int | None = None
    resolution: str = "1080p"
    views_count: int = 0
    likes_count: int = 0
    status: str
    hls_status: str | None = None
    created_at: datetime
    uploaded_at: str = "Just now"
    channel: ChannelInfo

    model_config = ConfigDict(from_attributes=True)


class VideoCatalogListResponse(BaseModel):
    items: list[VideoCatalogItem]
    total: int
    limit: int
    offset: int


class VideoDetailResponse(BaseModel):
    video: VideoCatalogItem
    related_videos: list[VideoCatalogItem] = Field(default_factory=list)


class CategoryItem(BaseModel):
    name: str
    video_count: int


class CategoryListResponse(BaseModel):
    categories: list[CategoryItem]
