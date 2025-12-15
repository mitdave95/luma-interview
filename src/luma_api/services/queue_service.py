"""Queue service for job management."""

import logging
from typing import Any

from redis.asyncio import Redis

from luma_api.config import UserTier
from luma_api.models.job import Job, QueuePriority
from luma_api.queue.priority_queue import PriorityQueue, QueuePosition, get_priority_queue

logger = logging.getLogger(__name__)


class QueueService:
    """
    Service for managing jobs in the priority queue.

    Maps user tiers to queue priorities and handles queue operations.
    """

    # Map user tiers to queue priorities
    TIER_PRIORITY_MAP = {
        UserTier.ENTERPRISE: QueuePriority.CRITICAL,
        UserTier.PRO: QueuePriority.HIGH,
        UserTier.DEVELOPER: QueuePriority.NORMAL,
    }

    def __init__(self, queue: PriorityQueue | None = None):
        self._queue = queue

    @property
    def queue(self) -> PriorityQueue:
        """Get the priority queue instance."""
        if self._queue is None:
            self._queue = get_priority_queue()
        return self._queue

    def get_priority_for_tier(self, tier: UserTier) -> QueuePriority:
        """Get the queue priority for a user tier."""
        return self.TIER_PRIORITY_MAP.get(tier, QueuePriority.NORMAL)

    async def enqueue_job(self, job: Job) -> QueuePosition:
        """
        Add a job to the queue based on its priority.

        Args:
            job: The job to enqueue

        Returns:
            QueuePosition with position and wait estimate
        """
        position = await self.queue.enqueue(job.id, job.priority)

        logger.info(
            "Job %s enqueued at position %d in %s queue",
            job.id,
            position.position,
            job.priority.value,
        )

        return position

    async def get_job_position(self, job: Job) -> QueuePosition | None:
        """Get the current queue position of a job."""
        position = await self.queue.get_position(job.id, job.priority)

        if position is None:
            return None

        estimated_wait = await self.queue._estimate_wait(position, job.priority)

        return QueuePosition(
            position=position,
            priority=job.priority,
            estimated_wait_seconds=estimated_wait,
        )

    async def cancel_job(self, job: Job) -> bool:
        """
        Remove a job from the queue.

        Returns:
            True if the job was removed, False if it wasn't in the queue
        """
        removed = await self.queue.remove(job.id, job.priority)

        if removed:
            logger.info("Job %s removed from queue", job.id)

        return removed

    async def dequeue_next_job(self) -> str | None:
        """
        Get the next job to process from the queue.

        Uses weighted fair queuing to balance between priority levels.

        Returns:
            Job ID or None if queue is empty
        """
        job_id = await self.queue.dequeue()

        if job_id:
            logger.debug("Dequeued job %s", job_id)

        return job_id

    async def get_queue_stats(self) -> dict[str, Any]:
        """Get statistics about all queues."""
        lengths = await self.queue.get_queue_lengths()

        return {
            "queues": {
                priority.value: {
                    "length": length,
                    "weight": PriorityQueue.WEIGHTS[priority],
                }
                for priority, length in lengths.items()
            },
            "total_jobs": sum(lengths.values()),
        }


# Singleton instance
_queue_service: QueueService | None = None


def get_queue_service(redis: Redis | None = None) -> QueueService:
    """Get queue service instance."""
    global _queue_service
    if _queue_service is None:
        queue = get_priority_queue(redis)
        _queue_service = QueueService(queue)
    return _queue_service


def reset_queue_service() -> None:
    """Reset queue service (for testing)."""
    global _queue_service
    _queue_service = None
