"""Generation request models."""

from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator

from luma_api.models.video import AspectRatio, Resolution, VideoStyle


class GenerationRequest(BaseModel):
    """Request to generate a video."""

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Text prompt describing the video to generate",
    )
    duration: int = Field(
        default=10,
        ge=1,
        le=300,
        description="Video duration in seconds",
    )
    resolution: Resolution = Field(
        default=Resolution.HD_1080P,
        description="Output video resolution",
    )
    style: VideoStyle | None = Field(
        default=None,
        description="Video style preset",
    )
    aspect_ratio: AspectRatio = Field(
        default=AspectRatio.RATIO_16_9,
        description="Video aspect ratio",
    )
    model: str = Field(
        default="dream-machine-1.5",
        description="Model to use for generation",
    )
    webhook_url: HttpUrl | None = Field(
        default=None,
        description="URL to call when generation completes",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Custom metadata to attach to the job",
    )

    @field_validator("prompt")
    @classmethod
    def validate_prompt_content(cls, v: str) -> str:
        """Validate prompt doesn't contain prohibited content."""
        # In a real implementation, this would check against a content policy
        prohibited_terms = ["explicit", "violence", "harmful"]
        lower_prompt = v.lower()
        for term in prohibited_terms:
            if term in lower_prompt:
                raise ValueError(f"Prompt contains prohibited content: {term}")
        return v


class BatchGenerationRequest(BaseModel):
    """Request to generate multiple videos."""

    requests: list[GenerationRequest] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of generation requests",
    )


class BatchGenerationResponse(BaseModel):
    """Response for batch generation request."""

    job_ids: list[str] = Field(..., description="List of created job IDs")
    total_queued: int = Field(..., description="Number of jobs queued")
