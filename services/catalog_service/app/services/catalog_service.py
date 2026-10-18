import json
import logging
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from app.core.config import settings
from app.repository.catalog import CatalogRepository
from app.schemas.catalog import (
    CategoryItem,
    CategoryListResponse,
    ChannelInfo,
    VideoCatalogItem,
    VideoCatalogListResponse,
    VideoDetailResponse,
    format_duration,
)

logger = logging.getLogger(__name__)


class CatalogService:
    """Business logic for video catalog discovery and metadata with Redis caching."""

    def __init__(self, repo: CatalogRepository, redis: Redis | None = None) -> None:
        self._repo = repo
        self._redis = redis

    def _determine_resolution(self, height: int | None) -> str:
        """Derive standard label from height."""
        if not height:
            return "1080p"
        if height >= 2160:
            return "4K"
        if height >= 1440:
            return "1440p"
        if height >= 1080:
            return "1080p"
        if height >= 720:
            return "720p"
        return "480p"

    async def _get_realtime_views(self, video_id: str, db_views: int) -> int:
        """Get live view count from Redis if tracked, falling back to DB."""
        if not self._redis:
            return db_views
        try:
            cached = await self._redis.hget(f"video:stats:{video_id}", "views")
            if cached is not None:
                return max(db_views, int(cached))
        except Exception as e:
            logger.debug("Failed to read realtime views from Redis: %s", e)
        return db_views

    async def _format_video_item(self, row: dict[str, Any]) -> VideoCatalogItem:
        """Map database row to VideoCatalogItem schema."""
        vid_id = str(row["id"])
        user_id = str(row["user_id"])
        username = row.get("username") or "creator"
        duration_sec = float(row.get("duration_seconds") or 0.0)
        db_views = int(row.get("views_count") or 0)
        views = await self._get_realtime_views(vid_id, db_views)

        channel = ChannelInfo(
            id=user_id,
            name=username,
            handle=f"@{username.lower()}",
            avatar=f"https://api.dicebear.com/7.x/initials/svg?seed={username}",
            subscribers="1.2K",
            verified=False,
        )

        return VideoCatalogItem(
            id=vid_id,
            title=row["title"],
            description=row.get("description"),
            category=row.get("category") or "General",
            thumbnail_url=row.get("thumbnail_url"),
            duration_seconds=duration_sec,
            duration=format_duration(duration_sec),
            width=row.get("width"),
            height=row.get("height"),
            resolution=self._determine_resolution(row.get("height")),
            views_count=views,
            likes_count=int(row.get("likes_count") or 0),
            status=row.get("status") or "ready",
            hls_status=row.get("hls_status"),
            created_at=row["created_at"],
            uploaded_at="Recent",
            channel=channel,
        )

    async def get_catalog(
        self,
        category: str | None = None,
        search: str | None = None,
        sort: str = "latest",
        limit: int = 50,
        offset: int = 0,
    ) -> VideoCatalogListResponse:
        """Retrieve paginated catalog videos with optional Redis caching."""
        cache_key = f"cache:catalog:list:{category or 'all'}:{search or 'none'}:{sort}:{limit}:{offset}"

        if settings.catalog_cache_enabled and self._redis:
            try:
                cached_data = await self._redis.get(cache_key)
                if cached_data:
                    data = json.loads(cached_data)
                    return VideoCatalogListResponse.model_validate(data)
            except Exception as e:
                logger.debug("Redis cache read skipped: %s", e)

        # Query database
        rows = await self._repo.list_videos(
            category=category,
            search=search,
            sort=sort,
            limit=limit,
            offset=offset,
        )
        total = await self._repo.count_videos(category=category, search=search)

        items = [await self._format_video_item(row) for row in rows]
        response = VideoCatalogListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

        # Store in Redis cache
        if settings.catalog_cache_enabled and self._redis:
            try:
                await self._redis.setex(
                    cache_key,
                    settings.catalog_cache_ttl_seconds,
                    response.model_dump_json(),
                )
            except Exception as e:
                logger.debug("Redis cache write skipped: %s", e)

        return response

    async def get_video_detail(
        self, video_id: UUID | str
    ) -> VideoDetailResponse | None:
        """Fetch video metadata and related catalog recommendations."""
        row = await self._repo.get_video_by_id(video_id)
        if not row:
            return None

        video = await self._format_video_item(row)
        related_rows = await self._repo.get_related_videos(
            video_id=video_id,
            category=video.category,
            limit=6,
        )
        related_videos = [await self._format_video_item(r) for r in related_rows]

        return VideoDetailResponse(video=video, related_videos=related_videos)

    async def get_categories(self) -> CategoryListResponse:
        """Fetch aggregated categories."""
        cache_key = "cache:catalog:categories"

        if settings.catalog_cache_enabled and self._redis:
            try:
                cached = await self._redis.get(cache_key)
                if cached:
                    return CategoryListResponse.model_validate_json(cached)
            except Exception as e:
                logger.debug("Categories cache read failed: %s", e)

        rows = await self._repo.get_categories_aggregation()
        categories = [
            CategoryItem(name=row["name"], video_count=int(row["video_count"]))
            for row in rows
        ]
        response = CategoryListResponse(categories=categories)

        if settings.catalog_cache_enabled and self._redis:
            try:
                await self._redis.setex(
                    cache_key,
                    settings.catalog_cache_ttl_seconds * 2,
                    response.model_dump_json(),
                )
            except Exception as e:
                logger.debug("Categories cache write failed: %s", e)

        return response
