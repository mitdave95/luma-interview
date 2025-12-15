"""Job service for managing video generation jobs."""

import logging
import uuid
from datetime import UTC, datetime

from luma_api.config import UserTier, get_tier_config
from luma_api.errors.exceptions import (
    InsufficientTierError,
    JobCancelledError,
    JobNotFoundError,
    PermissionDeniedError,
    QuotaExceededError,
)
from luma_api.models.generation import GenerationRequest
from luma_api.models.job import Job, JobResponse, JobStatus, can_transition
from luma_api.models.user import User
from luma_api.services.queue_service import QueueService, get_queue_service
from luma_api.storage.memory import InMemoryStorage, StorageManager, get_storage

logger = logging.getLogger(__name__)


class JobService:
    """Service for job management operations."""

    def __init__(
        self,
        storage: StorageManager | None = None,
        queue_service: QueueService | None = None,
    ):
        self._storage = storage
        self._queue_service = queue_service

    @property
    def storage(self) -> StorageManager:
        """Get storage manager."""
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    @property
    def jobs(self) -> InMemoryStorage[Job]:
        """Get job storage."""
        return self.storage.jobs

    @property
    def queue_service(self) -> QueueService:
        """Get queue service."""
        if self._queue_service is None:
            self._queue_service = get_queue_service()
        return self._queue_service

    async def create_job(
        self,
        request: GenerationRequest,
        user: User,
    ) -> Job:
        """
        Create a new video generation job.

        Args:
            request: Generation request parameters
            user: Current user

        Returns:
            Created Job object

        Raises:
            InsufficientTierError: If user can't generate
            QuotaExceededError: If daily quota exceeded
        """
        tier_config = get_tier_config(user.tier)

        # Check if user can generate
        if not tier_config.can_generate:
            raise InsufficientTierError(user.tier, UserTier.DEVELOPER)

        # Check video duration limit
        if request.duration > tier_config.max_video_duration:
            raise InsufficientTierError(
                user.tier,
                UserTier.PRO if request.duration <= 120 else UserTier.ENTERPRISE,
                details={
                    "requested_duration": request.duration,
                    "max_duration": tier_config.max_video_duration,
                },
            )

        # Check daily quota
        daily_usage = self.storage.usage.get_daily(user.id)
        if tier_config.daily_quota > 0 and daily_usage >= tier_config.daily_quota:
            raise QuotaExceededError(
                quota_type="daily",
                limit=tier_config.daily_quota,
                used=daily_usage,
            )

        # Check concurrent job limit
        active_jobs = self._count_active_jobs(user.id)
        if active_jobs >= tier_config.max_concurrent_jobs:
            raise QuotaExceededError(
                quota_type="concurrent_jobs",
                limit=tier_config.max_concurrent_jobs,
                used=active_jobs,
            )

        # Create job
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        priority = self.queue_service.get_priority_for_tier(user.tier)

        job = Job(
            id=job_id,
            user_id=user.id,
            status=JobStatus.PENDING,
            priority=priority,
            prompt=request.prompt,
            duration=request.duration,
            resolution=request.resolution.value,
            style=request.style.value if request.style else None,
            aspect_ratio=request.aspect_ratio.value,
            model=request.model,
            webhook_url=str(request.webhook_url) if request.webhook_url else None,
            request_metadata=request.metadata or {},
            created_at=datetime.now(UTC),
        )

        # Store job
        self.jobs.create(job)

        # Enqueue job
        position = await self.queue_service.enqueue_job(job)

        # Update job with queue info
        job.status = JobStatus.QUEUED
        job.queued_at = datetime.now(UTC)
        job.queue_position = position.position
        job.estimated_wait_seconds = position.estimated_wait_seconds
        self.jobs.update(job_id, job)

        logger.info(
            "Created job %s for user %s (priority: %s, position: %d)",
            job_id,
            user.id,
            priority.value,
            position.position,
        )

        return job

    def _count_active_jobs(self, user_id: str) -> int:
        """Count active (non-terminal) jobs for a user."""
        terminal_statuses = {
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.EXPIRED,
        }
        return self.jobs.count(lambda j: j.user_id == user_id and j.status not in terminal_statuses)

    def get_job(self, job_id: str, user: User) -> Job:
        """
        Get a job by ID.

        Args:
            job_id: Job identifier
            user: Current user

        Returns:
            Job object

        Raises:
            JobNotFoundError: If job doesn't exist
            PermissionDeniedError: If user doesn't own the job
        """
        job = self.jobs.get(job_id)

        if job is None:
            raise JobNotFoundError(job_id)

        if job.user_id != user.id:
            raise PermissionDeniedError(
                message="You don't have permission to access this job",
                details={"job_id": job_id},
            )

        return job

    def get_job_response(self, job_id: str, user: User) -> JobResponse:
        """Get job as API response format."""
        job = self.get_job(job_id, user)
        return JobResponse.from_job(job)

    def list_jobs(
        self,
        user: User,
        page: int = 1,
        per_page: int = 20,
        status: JobStatus | None = None,
    ) -> tuple[list[Job], int]:
        """
        List jobs for a user.

        Args:
            user: Current user
            page: Page number (1-indexed)
            per_page: Items per page
            status: Optional status filter

        Returns:
            Tuple of (jobs, total_count)
        """
        offset = (page - 1) * per_page

        def filter_fn(job: Job) -> bool:
            if job.user_id != user.id:
                return False
            if status and job.status != status:
                return False
            return True

        jobs, total = self.jobs.list(
            offset=offset,
            limit=per_page,
            filter_fn=filter_fn,
            sort_key="created_at",
            sort_desc=True,
        )

        return jobs, total

    async def cancel_job(self, job_id: str, user: User) -> Job:
        """
        Cancel a job.

        Args:
            job_id: Job identifier
            user: Current user

        Returns:
            Updated Job object

        Raises:
            JobNotFoundError: If job doesn't exist
            PermissionDeniedError: If user doesn't own the job
            JobCancelledError: If job can't be cancelled
        """
        job = self.get_job(job_id, user)

        # Check if job can be cancelled
        if not can_transition(job.status, JobStatus.CANCELLED):
            raise JobCancelledError(
                message=f"Job cannot be cancelled (current status: {job.status.value})",
                details={"job_id": job_id, "current_status": job.status.value},
            )

        # Remove from queue if queued
        if job.status == JobStatus.QUEUED:
            await self.queue_service.cancel_job(job)

        # Update status
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now(UTC)
        self.jobs.update(job_id, job)

        logger.info("Job %s cancelled", job_id)

        return job


# Singleton instance
_job_service: JobService | None = None


def get_job_service() -> JobService:
    """Get job service instance."""
    global _job_service
    if _job_service is None:
        _job_service = JobService()
    return _job_service


def reset_job_service() -> None:
    """Reset job service (for testing)."""
    global _job_service
    _job_service = None
