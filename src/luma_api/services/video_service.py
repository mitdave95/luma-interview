"""Video service for managing video resources."""

import logging

from luma_api.errors.exceptions import PermissionDeniedError, VideoNotFoundError
from luma_api.models.user import User
from luma_api.models.video import Video, VideoStatus
from luma_api.storage.memory import InMemoryStorage, StorageManager, get_storage

logger = logging.getLogger(__name__)


class VideoService:
    """Service for video CRUD operations."""

    def __init__(self, storage: StorageManager | None = None):
        self._storage = storage

    @property
    def videos(self) -> InMemoryStorage[Video]:
        """Get video storage."""
        if self._storage is None:
            self._storage = get_storage()
        return self._storage.videos

    def get_video(self, video_id: str, user: User) -> Video:
        """
        Get a video by ID.

        Args:
            video_id: Video identifier
            user: Current user (for ownership check)

        Returns:
            Video object

        Raises:
            VideoNotFoundError: If video doesn't exist
            PermissionDeniedError: If user doesn't own the video
        """
        video = self.videos.get(video_id)

        if video is None:
            raise VideoNotFoundError(video_id)

        # Check ownership
        if video.owner_id != user.id:
            raise PermissionDeniedError(
                message="You don't have permission to access this video",
                details={"video_id": video_id},
            )

        return video

    def list_videos(
        self,
        user: User,
        page: int = 1,
        per_page: int = 20,
        status: VideoStatus | None = None,
    ) -> tuple[list[Video], int]:
        """
        List videos for a user.

        Args:
            user: Current user
            page: Page number (1-indexed)
            per_page: Items per page
            status: Optional status filter

        Returns:
            Tuple of (videos, total_count)
        """
        offset = (page - 1) * per_page

        def filter_fn(video: Video) -> bool:
            # Must belong to user
            if video.owner_id != user.id:
                return False
            # Optional status filter
            if status and video.status != status:
                return False
            return True

        videos, total = self.videos.list(
            offset=offset,
            limit=per_page,
            filter_fn=filter_fn,
            sort_key="created_at",
            sort_desc=True,
        )

        return videos, total

    def get_stream_url(self, video_id: str, user: User) -> str:
        """
        Get streaming URL for a video.

        Args:
            video_id: Video identifier
            user: Current user

        Returns:
            Video stream URL

        Raises:
            VideoNotFoundError: If video doesn't exist or isn't ready
            PermissionDeniedError: If user doesn't own the video
        """
        video = self.get_video(video_id, user)

        if video.status != VideoStatus.READY:
            raise VideoNotFoundError(video_id)

        if video.url is None:
            raise VideoNotFoundError(video_id)

        # In a real implementation, this might generate a signed URL
        return str(video.url)

    def delete_video(self, video_id: str, user: User) -> bool:
        """
        Delete a video.

        Args:
            video_id: Video identifier
            user: Current user

        Returns:
            True if deleted

        Raises:
            VideoNotFoundError: If video doesn't exist
            PermissionDeniedError: If user doesn't own the video
        """
        # Verify ownership first
        self.get_video(video_id, user)

        return self.videos.delete(video_id)


# Singleton instance
_video_service: VideoService | None = None


def get_video_service() -> VideoService:
    """Get video service instance."""
    global _video_service
    if _video_service is None:
        _video_service = VideoService()
    return _video_service


def reset_video_service() -> None:
    """Reset video service (for testing)."""
    global _video_service
    _video_service = None
