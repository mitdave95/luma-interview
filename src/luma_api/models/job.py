"""Job models."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job processing status."""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class QueuePriority(str, Enum):
    """Queue priority levels."""

    CRITICAL = "critical"  # Enterprise
    HIGH = "high"  # Pro
    NORMAL = "normal"  # Developer


# Valid state transitions for jobs
JOB_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.PENDING: {JobStatus.QUEUED, JobStatus.CANCELLED},
    JobStatus.QUEUED: {JobStatus.PROCESSING, JobStatus.CANCELLED, JobStatus.EXPIRED},
    JobStatus.PROCESSING: {JobStatus.COMPLETED, JobStatus.FAILED},
    JobStatus.COMPLETED: set(),
    JobStatus.FAILED: set(),
    JobStatus.CANCELLED: set(),
    JobStatus.EXPIRED: set(),
}


def can_transition(from_status: JobStatus, to_status: JobStatus) -> bool:
    """Check if a job status transition is valid."""
    return to_status in JOB_TRANSITIONS.get(from_status, set())


class Job(BaseModel):
    """Video generation job model."""

    id: str = Field(..., description="Unique job identifier")
    user_id: str = Field(..., description="ID of the user who created this job")
    status: JobStatus = Field(default=JobStatus.PENDING)
    priority: QueuePriority = Field(default=QueuePriority.NORMAL)

    # Request details
    prompt: str = Field(..., description="Generation prompt")
    duration: int = Field(..., ge=1, le=300, description="Requested duration in seconds")
    resolution: str = Field(default="1080p")
    style: str | None = Field(default=None)
    aspect_ratio: str = Field(default="16:9")
    model: str = Field(default="dream-machine-1.5")
    webhook_url: str | None = Field(default=None)
    request_metadata: dict[str, Any] = Field(default_factory=dict)

    # Queue info
    queue_position: int | None = Field(default=None)
    estimated_wait_seconds: int | None = Field(default=None)

    # Progress
    progress: float | None = Field(default=None, ge=0, le=1)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    queued_at: datetime | None = Field(default=None)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    # Result
    video_id: str | None = Field(default=None, description="ID of generated video")
    error: str | None = Field(default=None, description="Error message if failed")

    # Retry handling
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)

    model_config = {"from_attributes": True}


class JobResponse(BaseModel):
    """API response for job status."""

    job_id: str
    status: JobStatus
    queue_position: int | None = None
    estimated_wait: str | None = None  # ISO 8601 duration format
    progress: float | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    video_id: str | None = None
    error: str | None = None

    @classmethod
    def from_job(cls, job: Job) -> "JobResponse":
        """Create response from job model."""
        estimated_wait = None
        if job.estimated_wait_seconds is not None:
            minutes, seconds = divmod(job.estimated_wait_seconds, 60)
            estimated_wait = f"PT{minutes}M{seconds}S"

        return cls(
            job_id=job.id,
            status=job.status,
            queue_position=job.queue_position,
            estimated_wait=estimated_wait,
            progress=job.progress,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            video_id=job.video_id,
            error=job.error,
        )
