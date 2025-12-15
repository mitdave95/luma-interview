"""Video endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Query

from luma_api.auth.dependencies import get_current_user
from luma_api.models.responses import PaginatedResponse
from luma_api.models.user import User
from luma_api.models.video import Video, VideoStatus
from luma_api.services.video_service import VideoService, get_video_service

router = APIRouter(prefix="/videos", tags=["Videos"])


@router.get(
    "",
    response_model=PaginatedResponse[Video],
    summary="List Videos",
    description="List all videos for the authenticated user with pagination.",
)
async def list_videos(
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: VideoStatus | None = Query(default=None, description="Filter by status"),
    user: User = Depends(get_current_user),
    video_service: VideoService = Depends(get_video_service),
) -> PaginatedResponse[Video]:
    """
    List videos belonging to the authenticated user.

    - Supports pagination with `page` and `per_page` parameters
    - Optional filtering by video status
    - Results are sorted by creation date (newest first)
    """
    videos, total = video_service.list_videos(
        user=user,
        page=page,
        per_page=per_page,
        status=status,
    )

    return PaginatedResponse.create(
        items=videos,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/{video_id}",
    response_model=Video,
    summary="Get Video",
    description="Get details of a specific video.",
)
async def get_video(
    video_id: str,
    user: User = Depends(get_current_user),
    video_service: VideoService = Depends(get_video_service),
) -> Video:
    """
    Get video details by ID.

    Returns the full video object including metadata, URLs, and status.
    Only the video owner can access their videos.
    """
    return video_service.get_video(video_id, user)


@router.get(
    "/{video_id}/stream",
    summary="Get Video Stream URL",
    description="Get the streaming URL for a video.",
)
async def get_video_stream(
    video_id: str,
    user: User = Depends(get_current_user),
    video_service: VideoService = Depends(get_video_service),
) -> dict[str, Any]:
    """
    Get the streaming URL for a video.

    The video must be in READY status. Returns a URL that can be used
    to stream or download the video content.

    In production, this would return a signed URL with limited validity.
    """
    url = video_service.get_stream_url(video_id, user)

    return {
        "video_id": video_id,
        "stream_url": url,
        "expires_in": 3600,  # 1 hour (mock)
    }


@router.delete(
    "/{video_id}",
    status_code=204,
    summary="Delete Video",
    description="Delete a video.",
)
async def delete_video(
    video_id: str,
    user: User = Depends(get_current_user),
    video_service: VideoService = Depends(get_video_service),
) -> None:
    """
    Delete a video.

    This permanently removes the video and its associated files.
    Only the video owner can delete their videos.
    """
    video_service.delete_video(video_id, user)
