"""Background worker for processing video generation jobs."""

import asyncio
import logging
import random
import uuid
from datetime import UTC, datetime

from luma_api.config import get_settings
from luma_api.errors.exceptions import GenerationError
from luma_api.models.job import Job, JobStatus, can_transition
from luma_api.models.video import AspectRatio, Resolution, Video, VideoStatus, VideoStyle
from luma_api.storage.memory import StorageManager, get_storage

logger = logging.getLogger(__name__)


class MockVideoGenerator:
    """Simulates video generation with realistic timing."""

    # Simulated failure rate for testing error handling
    FAILURE_RATE = 0.05  # 5%

    async def generate(self, job: Job) -> Video:
        """
        Simulate video generation.

        Processing time is based on video duration.
        Has a small chance of simulated failure for testing.

        Args:
            job: The generation job

        Returns:
            Generated Video object

        Raises:
            GenerationError: If generation fails (simulated)
        """
        # Simulate processing time (0.5 sec per second of video)
        base_time = job.duration * 0.5
        variance = random.uniform(0.8, 1.2)
        processing_time = base_time * variance

        logger.info(
            "Starting generation for job %s (%.1fs estimated)",
            job.id,
            processing_time,
        )

        # Simulate work in chunks for progress updates
        chunks = 10
        chunk_time = processing_time / chunks
        for i in range(chunks):
            await asyncio.sleep(chunk_time)
            # Could update progress here if needed

        # Random failure for testing (5% chance)
        if random.random() < self.FAILURE_RATE:
            raise GenerationError(
                message="Simulated generation failure",
                details={"reason": "random_failure", "job_id": job.id},
            )

        # Create the video
        video_id = f"vid_{uuid.uuid4().hex[:12]}"

        return Video(
            id=video_id,
            title=job.prompt[:50] if job.prompt else "Generated Video",
            description=job.prompt,
            duration=float(job.duration),
            resolution=Resolution(job.resolution) if job.resolution else Resolution.HD_1080P,
            aspect_ratio=AspectRatio(job.aspect_ratio)
            if job.aspect_ratio
            else AspectRatio.RATIO_16_9,
            style=VideoStyle(job.style) if job.style else None,
            status=VideoStatus.READY,
            url=f"https://mock-storage.lumalabs.ai/videos/{video_id}.mp4",
            thumbnail_url=f"https://mock-storage.lumalabs.ai/thumbs/{video_id}.jpg",
            created_at=datetime.now(UTC),
            owner_id=job.user_id,
            job_id=job.id,
        )


class JobWorker:
    """
    Background worker that processes video generation jobs.

    Polls the queue for jobs and processes them using the mock generator.
    """

    def __init__(
        self,
        storage: StorageManager | None = None,
        generator: MockVideoGenerator | None = None,
    ):
        self._storage = storage
        self._generator = generator or MockVideoGenerator()
        self._running = False
        self._settings = get_settings()
        self._task: asyncio.Task[None] | None = None

    @property
    def storage(self) -> StorageManager:
        """Get storage manager."""
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    async def start(self) -> None:
        """Start the worker."""
        if self._running:
            return

        if not self._settings.worker_enabled:
            logger.info("Worker disabled by configuration")
            return

        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Job worker started")

    async def stop(self) -> None:
        """Stop the worker gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Job worker stopped")

    async def _run(self) -> None:
        """Main worker loop."""
        from luma_api.services.queue_service import get_queue_service

        queue_service = get_queue_service()

        while self._running:
            try:
                # Poll for next job
                job_id = await queue_service.dequeue_next_job()

                if job_id:
                    await self._process_job(job_id)
                else:
                    # No jobs available, wait before polling again
                    await asyncio.sleep(self._settings.worker_poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Worker error: %s", e)
                await asyncio.sleep(1)  # Brief pause on error

    async def _process_job(self, job_id: str) -> None:
        """Process a single job."""
        # Get job from storage
        job = self.storage.jobs.get(job_id)
        if job is None:
            logger.warning("Job %s not found in storage", job_id)
            return

        # Update status to processing
        if not self._update_job_status(job, JobStatus.PROCESSING):
            return

        job.started_at = datetime.now(UTC)
        self.storage.jobs.update(job_id, job)

        try:
            # Generate video
            video = await self._generator.generate(job)

            # Store video
            self.storage.videos.create(video)

            # Update job as completed
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(UTC)
            job.video_id = video.id
            job.progress = 1.0
            self.storage.jobs.update(job_id, job)

            # Record usage
            self.storage.record_usage(
                user_id=job.user_id,
                videos_generated=1,
                duration_seconds=video.duration,
            )

            logger.info(
                "Job %s completed, video %s created",
                job_id,
                video.id,
            )

        except GenerationError as e:
            # Handle generation failure
            job.status = JobStatus.FAILED
            job.error = e.message
            job.completed_at = datetime.now(UTC)
            self.storage.jobs.update(job_id, job)

            logger.warning("Job %s failed: %s", job_id, e.message)

        except Exception as e:
            # Handle unexpected errors
            job.status = JobStatus.FAILED
            job.error = f"Unexpected error: {str(e)}"
            job.completed_at = datetime.now(UTC)
            self.storage.jobs.update(job_id, job)

            logger.exception("Job %s failed with unexpected error", job_id)

    def _update_job_status(self, job: Job, new_status: JobStatus) -> bool:
        """Update job status if transition is valid."""
        if not can_transition(job.status, new_status):
            logger.warning(
                "Invalid job transition for %s: %s -> %s",
                job.id,
                job.status.value,
                new_status.value,
            )
            return False

        job.status = new_status
        return True

    async def process_single(self, job_id: str) -> None:
        """Process a single job immediately (for testing)."""
        await self._process_job(job_id)


# Singleton instance
_worker: JobWorker | None = None


def get_worker() -> JobWorker:
    """Get worker instance."""
    global _worker
    if _worker is None:
        _worker = JobWorker()
    return _worker


def reset_worker() -> None:
    """Reset worker (for testing)."""
    global _worker
    if _worker:
        _worker._running = False
        if _worker._task:
            _worker._task.cancel()
        _worker._task = None
    _worker = None
