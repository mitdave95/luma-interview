"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from luma_api.models.generation import GenerationRequest
from luma_api.models.job import JobStatus, can_transition
from luma_api.models.video import AspectRatio, Resolution, Video, VideoStatus


class TestGenerationRequest:
    """Tests for GenerationRequest model."""

    def test_valid_request(self):
        """Test valid generation request."""
        req = GenerationRequest(
            prompt="A sunset over mountains",
            duration=10,
        )
        assert req.prompt == "A sunset over mountains"
        assert req.duration == 10
        assert req.resolution == Resolution.HD_1080P
        assert req.aspect_ratio == AspectRatio.RATIO_16_9

    def test_prompt_too_short(self):
        """Test that empty prompt fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationRequest(prompt="", duration=10)
        assert "prompt" in str(exc_info.value)

    def test_prompt_too_long(self):
        """Test that very long prompt fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationRequest(prompt="x" * 2001, duration=10)
        assert "prompt" in str(exc_info.value)

    def test_duration_too_short(self):
        """Test that duration less than 1 fails."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationRequest(prompt="test", duration=0)
        assert "duration" in str(exc_info.value)

    def test_duration_too_long(self):
        """Test that duration greater than 300 fails."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationRequest(prompt="test", duration=301)
        assert "duration" in str(exc_info.value)

    def test_prohibited_content(self):
        """Test that prohibited content in prompt fails."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationRequest(prompt="something explicit", duration=10)
        assert "prohibited" in str(exc_info.value).lower()

    def test_all_options(self):
        """Test request with all options specified."""
        req = GenerationRequest(
            prompt="A test video",
            duration=30,
            resolution=Resolution.UHD_4K,
            aspect_ratio=AspectRatio.RATIO_9_16,
            model="dream-machine-1.5",
            webhook_url="https://example.com/webhook",
            metadata={"project": "test"},
        )
        assert req.resolution == Resolution.UHD_4K
        assert req.aspect_ratio == AspectRatio.RATIO_9_16
        assert str(req.webhook_url) == "https://example.com/webhook"


class TestJobStatusTransitions:
    """Tests for job status state machine."""

    def test_pending_to_queued(self):
        """Test valid transition from PENDING to QUEUED."""
        assert can_transition(JobStatus.PENDING, JobStatus.QUEUED) is True

    def test_pending_to_cancelled(self):
        """Test valid transition from PENDING to CANCELLED."""
        assert can_transition(JobStatus.PENDING, JobStatus.CANCELLED) is True

    def test_pending_to_completed_invalid(self):
        """Test invalid transition from PENDING to COMPLETED."""
        assert can_transition(JobStatus.PENDING, JobStatus.COMPLETED) is False

    def test_queued_to_processing(self):
        """Test valid transition from QUEUED to PROCESSING."""
        assert can_transition(JobStatus.QUEUED, JobStatus.PROCESSING) is True

    def test_processing_to_completed(self):
        """Test valid transition from PROCESSING to COMPLETED."""
        assert can_transition(JobStatus.PROCESSING, JobStatus.COMPLETED) is True

    def test_processing_to_failed(self):
        """Test valid transition from PROCESSING to FAILED."""
        assert can_transition(JobStatus.PROCESSING, JobStatus.FAILED) is True

    def test_processing_to_cancelled_invalid(self):
        """Test invalid transition from PROCESSING to CANCELLED."""
        assert can_transition(JobStatus.PROCESSING, JobStatus.CANCELLED) is False

    def test_completed_is_terminal(self):
        """Test that COMPLETED is a terminal state."""
        assert can_transition(JobStatus.COMPLETED, JobStatus.FAILED) is False
        assert can_transition(JobStatus.COMPLETED, JobStatus.CANCELLED) is False

    def test_failed_is_terminal(self):
        """Test that FAILED is a terminal state."""
        assert can_transition(JobStatus.FAILED, JobStatus.COMPLETED) is False
        assert can_transition(JobStatus.FAILED, JobStatus.PROCESSING) is False


class TestVideo:
    """Tests for Video model."""

    def test_video_creation(self):
        """Test creating a video object."""
        video = Video(
            id="vid_123",
            title="Test Video",
            duration=10.0,
            resolution=Resolution.HD_1080P,
            status=VideoStatus.READY,
            owner_id="user_123",
        )
        assert video.id == "vid_123"
        assert video.title == "Test Video"
        assert video.status == VideoStatus.READY

    def test_video_with_url(self):
        """Test video with URL."""
        video = Video(
            id="vid_123",
            title="Test Video",
            duration=10.0,
            resolution=Resolution.HD_1080P,
            status=VideoStatus.READY,
            owner_id="user_123",
            url="https://example.com/video.mp4",
        )
        assert str(video.url) == "https://example.com/video.mp4"
