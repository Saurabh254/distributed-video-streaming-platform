import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import DbConnectionDep, RedisDep
from app.repository.catalog import CatalogRepository
from app.schemas.catalog import (
    CategoryListResponse,
    VideoCatalogListResponse,
    VideoDetailResponse,
)
from app.services.catalog_service import CatalogService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/catalog", tags=["catalog"])


def get_catalog_service(conn: DbConnectionDep, redis: RedisDep) -> CatalogService:
    repo = CatalogRepository(conn)
    return CatalogService(repo=repo, redis=redis)


CatalogServiceDep = Annotated[CatalogService, Depends := None]  # type helper


@router.get(
    "/videos",
    response_model=VideoCatalogListResponse,
    summary="List all videos in catalog",
)
async def list_videos(
    conn: DbConnectionDep,
    redis: RedisDep,
    category: Annotated[
        str | None,
        Query(description="Filter by category (e.g. Tech, Gaming, Design)"),
    ] = None,
    q: Annotated[
        str | None,
        Query(description="Search keyword in title, description, or creator"),
    ] = None,
    sort: Annotated[
        str,
        Query(description="Sort order: 'latest', 'views', or 'duration'"),
    ] = "latest",
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Items per page"),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0, description="Pagination offset"),
    ] = 0,
) -> VideoCatalogListResponse:
    """Retrieve all videos from catalog with filtering, search, and pagination."""
    service = get_catalog_service(conn, redis)
    return await service.get_catalog(
        category=category,
        search=q,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/videos/{video_id}",
    response_model=VideoDetailResponse,
    summary="Get video catalog details",
)
async def get_video(
    video_id: UUID,
    conn: DbConnectionDep,
    redis: RedisDep,
) -> VideoDetailResponse:
    """Retrieve full catalog details and related videos for a single video."""
    service = get_catalog_service(conn, redis)
    detail = await service.get_video_detail(video_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video '{video_id}' not found in catalog",
        )
    return detail


@router.get(
    "/categories",
    response_model=CategoryListResponse,
    summary="List all categories",
)
async def list_categories(
    conn: DbConnectionDep,
    redis: RedisDep,
) -> CategoryListResponse:
    """Retrieve distinct video categories and count of videos in each."""
    service = get_catalog_service(conn, redis)
    return await service.get_categories()
