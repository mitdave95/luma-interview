"""Redis-based priority queue with weighted fair queuing."""

import logging
import random
import time
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis

from luma_api.models.job import QueuePriority
from luma_api.queue.lua_scripts import lua_scripts

logger = logging.getLogger(__name__)


@dataclass
class QueuePosition:
    """Information about a job's position in the queue."""

    position: int  # 1-indexed position
    priority: QueuePriority
    estimated_wait_seconds: int


class PriorityQueue:
    """
    Redis-based priority queue with weighted fair queuing.

    Uses Redis sorted sets for each priority level:
    - critical: Enterprise tier (weight: 10)
    - high: Pro tier (weight: 5)
    - normal: Developer tier (weight: 1)

    Dequeue uses weighted fair queuing (10:5:1 ratio) to ensure
    fair processing while prioritizing higher tiers.
    """

    # Queue keys by priority
    QUEUE_KEYS = {
        QueuePriority.CRITICAL: "queue:critical",
        QueuePriority.HIGH: "queue:high",
        QueuePriority.NORMAL: "queue:normal",
    }

    # Weighted fair queuing weights
    WEIGHTS = {
        QueuePriority.CRITICAL: 10,
        QueuePriority.HIGH: 5,
        QueuePriority.NORMAL: 1,
    }

    # Estimated processing time per job (seconds)
    ESTIMATED_PROCESSING_TIME = 30

    def __init__(self, redis: Redis | None = None):
        self._redis = redis
        # In-memory fallback queues
        self._local_queues: dict[QueuePriority, list[tuple[str, float]]] = {
            QueuePriority.CRITICAL: [],
            QueuePriority.HIGH: [],
            QueuePriority.NORMAL: [],
        }

    async def enqueue(
        self,
        job_id: str,
        priority: QueuePriority,
    ) -> QueuePosition:
        """
        Add a job to the appropriate priority queue.

        Args:
            job_id: Unique job identifier
            priority: Queue priority level

        Returns:
            QueuePosition with position and wait estimate
        """
        score = time.time()  # FIFO within priority level

        if self._redis:
            position = await self._enqueue_redis(job_id, priority, score)
        else:
            position = self._enqueue_local(job_id, priority, score)

        # Estimate wait time based on position and weights
        estimated_wait = await self._estimate_wait(position, priority)

        return QueuePosition(
            position=position,
            priority=priority,
            estimated_wait_seconds=estimated_wait,
        )

    async def _enqueue_redis(
        self,
        job_id: str,
        priority: QueuePriority,
        score: float,
    ) -> int:
        """Enqueue using Redis."""
        key = self.QUEUE_KEYS[priority]
        redis = self._redis
        assert redis is not None

        try:
            if lua_scripts.queue_enqueue_sha:
                position: Any = await redis.evalsha(  # type: ignore[misc]
                    lua_scripts.queue_enqueue_sha,
                    1,
                    key,
                    job_id,
                    score,
                )
            else:
                await redis.zadd(key, {job_id: score})
                position = await redis.zrank(key, job_id)
                position = (position or 0) + 1

            return int(position)
        except Exception as e:
            logger.warning("Redis enqueue error, using local: %s", e)
            return self._enqueue_local(job_id, priority, score)

    def _enqueue_local(
        self,
        job_id: str,
        priority: QueuePriority,
        score: float,
    ) -> int:
        """Enqueue using in-memory queue."""
        queue = self._local_queues[priority]
        queue.append((job_id, score))
        queue.sort(key=lambda x: x[1])  # Sort by score (FIFO)
        return len(queue)

    async def dequeue(self) -> str | None:
        """
        Dequeue a job using weighted fair queuing.

        Higher priority queues get more processing share:
        - Critical: 10 parts
        - High: 5 parts
        - Normal: 1 part

        Returns:
            Job ID or None if all queues are empty
        """
        if self._redis:
            return await self._dequeue_redis()
        return self._dequeue_local()

    async def _dequeue_redis(self) -> str | None:
        """Dequeue from Redis using weighted selection."""
        # Weighted random selection of queue
        priorities = [QueuePriority.CRITICAL, QueuePriority.HIGH, QueuePriority.NORMAL]
        total_weight = sum(self.WEIGHTS.values())
        choice = random.randint(1, total_weight)

        cumulative = 0
        for priority in priorities:
            cumulative += self.WEIGHTS[priority]
            if choice <= cumulative:
                job_id = await self._pop_from_redis_queue(priority)
                if job_id:
                    return job_id
                break

        # Fallback: try all queues in priority order
        for priority in priorities:
            job_id = await self._pop_from_redis_queue(priority)
            if job_id:
                return job_id

        return None

    async def _pop_from_redis_queue(self, priority: QueuePriority) -> str | None:
        """Pop the oldest job from a Redis queue."""
        key = self.QUEUE_KEYS[priority]
        redis = self._redis
        assert redis is not None

        try:
            if lua_scripts.queue_dequeue_sha:
                result: Any = await redis.evalsha(  # type: ignore[misc]
                    lua_scripts.queue_dequeue_sha,
                    1,
                    key,
                )
                return str(result) if result else None
            else:
                # Non-atomic fallback
                items: list[Any] = await redis.zrange(key, 0, 0)
                if not items:
                    return None
                job_id = str(items[0])
                await redis.zrem(key, job_id)
                return job_id
        except Exception as e:
            logger.warning("Redis dequeue error: %s", e)
            return None

    def _dequeue_local(self) -> str | None:
        """Dequeue from local queues using weighted selection."""
        priorities = [QueuePriority.CRITICAL, QueuePriority.HIGH, QueuePriority.NORMAL]
        total_weight = sum(self.WEIGHTS.values())
        choice = random.randint(1, total_weight)

        cumulative = 0
        for priority in priorities:
            cumulative += self.WEIGHTS[priority]
            if choice <= cumulative:
                if self._local_queues[priority]:
                    return self._local_queues[priority].pop(0)[0]
                break

        # Fallback: try all queues in priority order
        for priority in priorities:
            if self._local_queues[priority]:
                return self._local_queues[priority].pop(0)[0]

        return None

    async def get_position(
        self,
        job_id: str,
        priority: QueuePriority,
    ) -> int | None:
        """Get the current position of a job in the queue."""
        if self._redis:
            redis = self._redis
            key = self.QUEUE_KEYS[priority]
            try:
                if lua_scripts.queue_position_sha:
                    position: Any = await redis.evalsha(  # type: ignore[misc]
                        lua_scripts.queue_position_sha,
                        1,
                        key,
                        job_id,
                    )
                else:
                    position = await redis.zrank(key, job_id)
                    if position is not None:
                        position += 1

                return int(position) if position and position > 0 else None
            except Exception as e:
                logger.warning("Redis get_position error: %s", e)

        # Local fallback
        queue = self._local_queues[priority]
        for i, (jid, _) in enumerate(queue):
            if jid == job_id:
                return i + 1
        return None

    async def remove(self, job_id: str, priority: QueuePriority) -> bool:
        """Remove a job from the queue."""
        if self._redis:
            redis = self._redis
            key = self.QUEUE_KEYS[priority]
            try:
                removed: int = await redis.zrem(key, job_id)
                return removed > 0
            except Exception as e:
                logger.warning("Redis remove error: %s", e)

        # Local fallback
        queue = self._local_queues[priority]
        for i, (jid, _) in enumerate(queue):
            if jid == job_id:
                queue.pop(i)
                return True
        return False

    async def get_queue_lengths(self) -> dict[QueuePriority, int]:
        """Get the length of each priority queue."""
        lengths = {}

        if self._redis:
            try:
                for priority, key in self.QUEUE_KEYS.items():
                    lengths[priority] = await self._redis.zcard(key)
                return lengths
            except Exception as e:
                logger.warning("Redis get_queue_lengths error: %s", e)

        # Local fallback
        for priority in QueuePriority:
            lengths[priority] = len(self._local_queues[priority])
        return lengths

    async def _estimate_wait(self, position: int, priority: QueuePriority) -> int:
        """Estimate wait time in seconds based on position and priority."""
        # Get queue lengths
        lengths = await self.get_queue_lengths()

        # Jobs ahead in same priority queue
        jobs_ahead = position - 1

        # Factor in higher priority queues
        if priority == QueuePriority.NORMAL:
            # Normal jobs wait for critical and high priority jobs too
            weight_factor = 0.3  # Reduced weight due to fair queuing
            jobs_ahead += int(lengths.get(QueuePriority.CRITICAL, 0) * weight_factor)
            jobs_ahead += int(lengths.get(QueuePriority.HIGH, 0) * weight_factor * 0.5)
        elif priority == QueuePriority.HIGH:
            # High jobs mainly wait for critical
            weight_factor = 0.5
            jobs_ahead += int(lengths.get(QueuePriority.CRITICAL, 0) * weight_factor)

        # Estimate based on jobs ahead * processing time
        return jobs_ahead * self.ESTIMATED_PROCESSING_TIME

    async def get_queue_jobs(
        self,
        priority: QueuePriority,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get jobs in a specific queue with their timestamps.

        Args:
            priority: The queue priority to query
            limit: Maximum number of jobs to return

        Returns:
            List of dicts with job_id and enqueued_at timestamp
        """
        if self._redis:
            key = self.QUEUE_KEYS[priority]
            try:
                jobs = await self._redis.zrange(key, 0, limit - 1, withscores=True)
                return [{"job_id": job_id, "enqueued_at": score} for job_id, score in jobs]
            except Exception as e:
                logger.warning("Redis get_queue_jobs error: %s", e)

        # Local fallback
        queue = self._local_queues[priority][:limit]
        return [{"job_id": job_id, "enqueued_at": score} for job_id, score in queue]

    async def get_queue_jobs_all(self, limit: int = 50) -> dict[str, list[dict[str, Any]]]:
        """
        Get jobs from all priority queues.

        Args:
            limit: Maximum number of jobs per queue

        Returns:
            Dict mapping priority name to list of job data
        """
        result = {}
        for priority in QueuePriority:
            jobs = await self.get_queue_jobs(priority, limit)
            result[priority.value] = jobs
        return result

    def clear_local(self) -> None:
        """Clear local queues (for testing)."""
        for queue in self._local_queues.values():
            queue.clear()


# Singleton instance
_priority_queue: PriorityQueue | None = None


def get_priority_queue(redis: Redis | None = None) -> PriorityQueue:
    """Get priority queue instance."""
    global _priority_queue
    if _priority_queue is None:
        _priority_queue = PriorityQueue(redis)
    elif redis and _priority_queue._redis is None:
        _priority_queue._redis = redis
    return _priority_queue


def reset_priority_queue() -> None:
    """Reset priority queue (for testing)."""
    global _priority_queue
    _priority_queue = None
