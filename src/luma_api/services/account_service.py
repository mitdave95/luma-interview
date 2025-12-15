"""Account service for user account and usage management."""

import logging
from datetime import UTC, datetime, timedelta

from luma_api.config import get_tier_config
from luma_api.models.responses import AccountResponse, QuotaResponse, UsageResponse
from luma_api.models.user import User
from luma_api.services.rate_limit_service import RateLimitService, get_rate_limit_service
from luma_api.storage.memory import StorageManager, get_storage

logger = logging.getLogger(__name__)


class AccountService:
    """Service for account and usage operations."""

    def __init__(
        self,
        storage: StorageManager | None = None,
        rate_limit_service: RateLimitService | None = None,
    ):
        self._storage = storage
        self._rate_limit_service = rate_limit_service

    @property
    def storage(self) -> StorageManager:
        """Get storage manager."""
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    @property
    def rate_limiter(self) -> RateLimitService:
        """Get rate limit service."""
        if self._rate_limit_service is None:
            self._rate_limit_service = get_rate_limit_service()
        return self._rate_limit_service

    def get_account(self, user: User) -> AccountResponse:
        """Get account details for a user."""
        return AccountResponse(
            user_id=user.id,
            email=user.email,
            tier=user.tier.value,
            created_at=user.created_at,
            is_active=user.is_active,
        )

    def get_usage(self, user: User, period: str = "daily") -> UsageResponse:
        """
        Get usage statistics for a user.

        Args:
            user: Current user
            period: "daily" or "monthly"

        Returns:
            UsageResponse with usage statistics
        """
        now = datetime.now(UTC)

        if period == "daily":
            requests_made = self.storage.usage.get_daily(user.id)
            period_start = datetime(now.year, now.month, now.day, tzinfo=UTC)
            period_end = period_start + timedelta(days=1)
        else:  # monthly
            requests_made = self.storage.usage.get_monthly(user.id)
            period_start = datetime(now.year, now.month, 1, tzinfo=UTC)
            # Calculate end of month
            if now.month == 12:
                period_end = datetime(now.year + 1, 1, 1, tzinfo=UTC)
            else:
                period_end = datetime(now.year, now.month + 1, 1, tzinfo=UTC)

        # Get detailed usage (videos, duration)
        usage_details = self.storage.get_usage_details(user.id)

        return UsageResponse(
            user_id=user.id,
            tier=user.tier.value,
            period=period,
            requests_made=requests_made,
            videos_generated=usage_details.get("videos_generated", 0),
            total_duration_seconds=usage_details.get("total_duration_seconds", 0.0),
            period_start=period_start,
            period_end=period_end,
        )

    async def get_quota(self, user: User) -> QuotaResponse:
        """
        Get quota information for a user.

        Args:
            user: Current user

        Returns:
            QuotaResponse with quota limits and usage
        """
        tier_config = get_tier_config(user.tier)

        # Get rate limit status
        rate_limit = await self.rate_limiter.get_current_usage(
            user_id=user.id,
            tier=user.tier,
        )

        # Get daily usage
        daily_usage = self.storage.usage.get_daily(user.id)
        daily_limit = tier_config.daily_quota
        daily_remaining = max(0, daily_limit - daily_usage) if daily_limit > 0 else -1

        # Count active jobs
        from luma_api.models.job import JobStatus

        terminal_statuses = {
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.EXPIRED,
        }
        active_jobs = self.storage.jobs.count(
            lambda j: j.user_id == user.id and j.status not in terminal_statuses
        )

        return QuotaResponse(
            user_id=user.id,
            tier=user.tier.value,
            rate_limit={
                "limit": rate_limit.limit,
                "remaining": rate_limit.remaining,
                "reset": rate_limit.reset_at,
                "window_seconds": rate_limit.window_seconds,
            },
            daily_quota={
                "limit": daily_limit if daily_limit > 0 else "unlimited",
                "used": daily_usage,
                "remaining": daily_remaining if daily_limit > 0 else "unlimited",
            },
            concurrent_jobs={
                "limit": tier_config.max_concurrent_jobs,
                "active": active_jobs,
                "available": max(0, tier_config.max_concurrent_jobs - active_jobs),
            },
            max_video_duration=tier_config.max_video_duration,
            can_generate=tier_config.can_generate,
            can_batch_generate=tier_config.can_batch_generate,
        )


# Singleton instance
_account_service: AccountService | None = None


def get_account_service() -> AccountService:
    """Get account service instance."""
    global _account_service
    if _account_service is None:
        _account_service = AccountService()
    return _account_service


def reset_account_service() -> None:
    """Reset account service (for testing)."""
    global _account_service
    _account_service = None
