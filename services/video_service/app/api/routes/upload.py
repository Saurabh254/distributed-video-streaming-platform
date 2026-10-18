from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUserDep, UploadServiceDep
from app.schemas.video import (
    VideoListResponse,
    VideoResponse,
    VideoUploadCompleteRequest,
    VideoUploadInitiateRequest,
    VideoUploadInitiateResponse,
)

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post(
    "/initiate-upload",
    response_model=VideoUploadInitiateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a video upload and retrieve a presigned S3 PUT URL",
)
async def initiate_upload(
    payload: VideoUploadInitiateRequest,
    current_user: CurrentUserDep,
    upload_service: UploadServiceDep,
):
    return await upload_service.initiate_upload(
        user_id=current_user["id"],
        req=payload,
    )


@router.post(
    "/{video_id}/complete",
    response_model=VideoResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm video upload completion and verify object in storage",
)
async def complete_upload(
    video_id: UUID,
    current_user: CurrentUserDep,
    upload_service: UploadServiceDep,
    payload: VideoUploadCompleteRequest | None = None,
):
    return await upload_service.complete_upload(
        video_id=video_id,
        user_id=current_user["id"],
        req=payload,
    )


@router.get(
    "/{video_id}",
    response_model=VideoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get video details and current upload/processing status",
)
async def get_video(
    video_id: UUID,
    current_user: CurrentUserDep,
    upload_service: UploadServiceDep,
):
    return await upload_service.get_video(
        video_id=video_id,
        user_id=current_user["id"],
    )


@router.get(
    "",
    response_model=VideoListResponse,
    status_code=status.HTTP_200_OK,
    summary="List videos uploaded by the authenticated user",
)
async def list_videos(
    current_user: CurrentUserDep,
    upload_service: UploadServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await upload_service.list_user_videos(
        user_id=current_user["id"],
        limit=limit,
        offset=offset,
    )
