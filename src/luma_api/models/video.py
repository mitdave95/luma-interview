"""Video models."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class VideoStatus(str, Enum):
    """Video processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Resolution(str, Enum):
    """Video resolution options."""

    SD_480P = "480p"
    HD_720P = "720p"
    HD_1080P = "1080p"
    UHD_4K = "4k"


class AspectRatio(str, Enum):
    """Video aspect ratio options."""

    RATIO_16_9 = "16:9"
    RATIO_9_16 = "9:16"
    RATIO_1_1 = "1:1"
    RATIO_4_3 = "4:3"


class VideoStyle(str, Enum):
    """Video style options."""

    CINEMATIC = "cinematic"
    ANIME = "anime"
    REALISTIC = "realistic"
    ARTISTIC = "artistic"
    DOCUMENTARY = "documentary"


class Video(BaseModel):
    """Video model."""

    id: str = Field(..., description="Unique video identifier")
    title: str = Field(..., description="Video title")
    description: str | None = Field(default=None, description="Video description")
    duration: float = Field(..., ge=0, description="Video duration in seconds")
    resolution: Resolution = Field(..., description="Video resolution")
    aspect_ratio: AspectRatio = Field(default=AspectRatio.RATIO_16_9)
    style: VideoStyle | None = Field(default=None)
    status: VideoStatus = Field(..., description="Current processing status")
    url: str | None = Field(default=None, description="Video URL when ready")
    thumbnail_url: str | None = Field(default=None, description="Thumbnail URL")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    owner_id: str = Field(..., description="ID of the user who owns this video")
    job_id: str | None = Field(default=None, description="Associated job ID")
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}
