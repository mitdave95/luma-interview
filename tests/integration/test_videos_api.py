"""Integration tests for video endpoints."""

import pytest

from luma_api.models.video import Resolution, Video, VideoStatus
from luma_api.storage.memory import get_storage


class TestVideosAPI:
    """Tests for /v1/videos endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self, client, dev_user):
        """Set up test data."""
        storage = get_storage()
        # Create some test videos
        for i in range(3):
            video = Video(
                id=f"vid_{i}",
                title=f"Test Video {i}",
                description=f"Description {i}",
                duration=10.0,
                resolution=Resolution.HD_1080P,
                status=VideoStatus.READY,
                url=f"https://example.com/video_{i}.mp4",
                owner_id=dev_user.id,
            )
            storage.videos.create(video)

    def test_list_videos_authenticated(self, client, dev_user_headers):
        """Test listing videos with valid authentication."""
        response = client.get("/v1/videos", headers=dev_user_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "meta" in data
        assert len(data["items"]) == 3
        assert data["meta"]["total"] == 3

    def test_list_videos_unauthenticated(self, client):
        """Test listing videos without authentication."""
        response = client.get("/v1/videos")
        assert response.status_code == 401

    def test_list_videos_invalid_key(self, client, invalid_user_headers):
        """Test listing videos with invalid API key."""
        response = client.get("/v1/videos", headers=invalid_user_headers)
        assert response.status_code == 401

    def test_list_videos_pagination(self, client, dev_user_headers):
        """Test pagination for video list."""
        response = client.get(
            "/v1/videos",
            params={"page": 1, "per_page": 2},
            headers=dev_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["meta"]["total"] == 3
        assert data["meta"]["has_next"] is True

    def test_list_videos_filter_by_status(self, client, dev_user_headers):
        """Test filtering videos by status."""
        response = client.get(
            "/v1/videos",
            params={"status": "ready"},
            headers=dev_user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for video in data["items"]:
            assert video["status"] == "ready"

    def test_get_video_success(self, client, dev_user_headers):
        """Test getting a specific video."""
        response = client.get("/v1/videos/vid_0", headers=dev_user_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "vid_0"
        assert data["title"] == "Test Video 0"

    def test_get_video_not_found(self, client, dev_user_headers):
        """Test getting a non-existent video."""
        response = client.get("/v1/videos/vid_nonexistent", headers=dev_user_headers)
        assert response.status_code == 404

    def test_get_video_wrong_owner(self, client, free_user_headers):
        """Test getting video owned by another user."""
        response = client.get("/v1/videos/vid_0", headers=free_user_headers)
        assert response.status_code == 403

    def test_get_stream_url(self, client, dev_user_headers):
        """Test getting stream URL for a video."""
        response = client.get("/v1/videos/vid_0/stream", headers=dev_user_headers)
        assert response.status_code == 200
        data = response.json()
        assert "stream_url" in data
        assert data["video_id"] == "vid_0"

    def test_delete_video(self, client, dev_user_headers):
        """Test deleting a video."""
        response = client.delete("/v1/videos/vid_0", headers=dev_user_headers)
        assert response.status_code == 204

        # Verify it's gone
        response = client.get("/v1/videos/vid_0", headers=dev_user_headers)
        assert response.status_code == 404

    def test_rate_limit_headers_present(self, client, dev_user_headers):
        """Test that rate limit headers are present."""
        response = client.get("/v1/videos", headers=dev_user_headers)
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
