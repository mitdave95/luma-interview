"""Rate limiting service with sliding window algorithm."""

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis

from luma_api.config import UserTier, get_tier_config
from luma_api.queue.lua_scripts import RATE_LIMIT_SCRIPT, lua_scripts

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    limit: int
    remaining: int
    reset_at: int  # Unix timestamp
    window_seconds: int

    @property
    def retry_after(self) -> int:
        """Seconds until rate limit resets."""
        return max(0, self.reset_at - int(time.time()))


class RateLimitService:
    """
    Rate limiting service using sliding window log algorithm.

    Uses Redis sorted sets to track request timestamps within a sliding window.
    Requests are scored by timestamp, allowing efficient range queries.
    """

    def __init__(self, redis: Redis | None = None):
        self._redis = redis
        self._local_counts: dict[str, list[float]] = {}  # Fallback for no Redis

    def _get_key(self, user_id: str, endpoint: str = "default") -> str:
        """Generate Redis key for rate limiting."""
        return f"rate_limit:{user_id}:{endpoint}"

    async def check_and_increment(
        self,
        user_id: str,
        tier: UserTier,
        endpoint: str = "default",
    ) -> RateLimitResult:
        """
        Check rate limit and increment counter if allowed.

        Args:
            user_id: User identifier
            tier: User's subscription tier
            endpoint: Optional endpoint-specific limiting

        Returns:
            RateLimitResult with allowed status and metadata
        """
        tier_config = get_tier_config(tier)
        limit = tier_config.rate_limit_per_minute
        window_seconds = 60

        # Use Redis if available
        if self._redis:
            return await self._check_redis(user_id, endpoint, limit, window_seconds)

        # Fallback to in-memory (not suitable for production)
        return self._check_local(user_id, endpoint, limit, window_seconds)

    async def _check_redis(
        self,
        user_id: str,
        endpoint: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        """Check rate limit using Redis."""
        key = self._get_key(user_id, endpoint)
        now = time.time()
        request_id = str(uuid.uuid4())

        redis = self._redis
        assert redis is not None

        try:
            # Use Lua script for atomic operation
            if lua_scripts.rate_limit_sha:
                result: Any = await redis.evalsha(  # type: ignore[misc]
                    lua_scripts.rate_limit_sha,
                    1,
                    key,
                    window_seconds,
                    limit,
                    now,
                    request_id,
                )
            else:
                # Fallback to inline script
                result = await redis.eval(  # type: ignore[misc]
                    RATE_LIMIT_SCRIPT,
                    1,
                    key,
                    window_seconds,
                    limit,
                    now,
                    request_id,
                )

            allowed = bool(result[0])
            remaining = int(result[1])
            reset_at = int(result[2])

            return RateLimitResult(
                allowed=allowed,
                limit=limit,
                remaining=remaining,
                reset_at=reset_at,
                window_seconds=window_seconds,
            )

        except Exception as e:
            logger.warning("Redis rate limit error, allowing request: %s", e)
            # Fail open - allow the request if Redis fails
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit - 1,
                reset_at=int(now + window_seconds),
                window_seconds=window_seconds,
            )

    def _check_local(
        self,
        user_id: str,
        endpoint: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        """Check rate limit using in-memory storage (fallback)."""
        key = self._get_key(user_id, endpoint)
        now = time.time()
        cutoff = now - window_seconds

        # Initialize if needed
        if key not in self._local_counts:
            self._local_counts[key] = []

        # Remove expired entries
        self._local_counts[key] = [ts for ts in self._local_counts[key] if ts > cutoff]

        count = len(self._local_counts[key])

        if count < limit:
            self._local_counts[key].append(now)
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit - count - 1,
                reset_at=int(now + window_seconds),
                window_seconds=window_seconds,
            )

        # Calculate reset time from oldest request
        oldest = min(self._local_counts[key]) if self._local_counts[key] else now
        reset_at = int(oldest + window_seconds)

        return RateLimitResult(
            allowed=False,
            limit=limit,
            remaining=0,
            reset_at=reset_at,
            window_seconds=window_seconds,
        )

    async def get_current_usage(
        self,
        user_id: str,
        tier: UserTier,
        endpoint: str = "default",
    ) -> RateLimitResult:
        """
        Get current rate limit status without incrementing.

        Useful for quota endpoints.
        """
        tier_config = get_tier_config(tier)
        limit = tier_config.rate_limit_per_minute
        window_seconds = 60
        key = self._get_key(user_id, endpoint)
        now = time.time()

        if self._redis:
            try:
                # Remove expired and count
                cutoff = now - window_seconds
                await self._redis.zremrangebyscore(key, 0, cutoff)
                count = await self._redis.zcard(key)

                return RateLimitResult(
                    allowed=count < limit,
                    limit=limit,
                    remaining=max(0, limit - count),
                    reset_at=int(now + window_seconds),
                    window_seconds=window_seconds,
                )
            except Exception as e:
                logger.warning("Redis error getting usage: %s", e)

        # Fallback
        if key in self._local_counts:
            cutoff = now - window_seconds
            self._local_counts[key] = [ts for ts in self._local_counts[key] if ts > cutoff]
            count = len(self._local_counts[key])
        else:
            count = 0

        return RateLimitResult(
            allowed=count < limit,
            limit=limit,
            remaining=max(0, limit - count),
            reset_at=int(now + window_seconds),
            window_seconds=window_seconds,
        )

    async def get_all_user_limits(self) -> dict[str, dict[str, Any]]:
        """
        Get rate limit status for all mock users.

        Returns:
            Dict mapping user_id to rate limit status
        """
        from luma_api.auth.mock_auth import MOCK_USERS

        results = {}
        for api_key, user in MOCK_USERS.items():
            result = await self.get_current_usage(
                user_id=user.id,
                tier=user.tier,
            )
            results[user.id] = {
                "user_id": user.id,
                "tier": user.tier.value,
                "limit": result.limit,
                "remaining": result.remaining,
                "reset_at": result.reset_at,
                "is_rate_limited": result.remaining == 0,
            }
        return results

    def clear_local(self) -> None:
        """Clear local rate limit data (for testing)."""
        self._local_counts.clear()


# Singleton instance
_rate_limit_service: RateLimitService | None = None


def get_rate_limit_service(redis: Redis | None = None) -> RateLimitService:
    """Get rate limit service instance."""
    global _rate_limit_service
    if _rate_limit_service is None:
        _rate_limit_service = RateLimitService(redis)
    elif redis and _rate_limit_service._redis is None:
        _rate_limit_service._redis = redis
    return _rate_limit_service


def reset_rate_limit_service() -> None:
    """Reset rate limit service (for testing)."""
    global _rate_limit_service
    _rate_limit_service = None
