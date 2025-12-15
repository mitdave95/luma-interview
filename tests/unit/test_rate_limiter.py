"""Tests for rate limiting service."""

import pytest

from luma_api.config import UserTier
from luma_api.services.rate_limit_service import RateLimitService


class TestRateLimitService:
    """Tests for RateLimitService with in-memory fallback."""

    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter without Redis."""
        service = RateLimitService(redis=None)
        yield service
        service.clear_local()

    @pytest.mark.asyncio
    async def test_allows_requests_under_limit(self, rate_limiter):
        """Test that requests under limit are allowed."""
        result = await rate_limiter.check_and_increment(
            user_id="user_1",
            tier=UserTier.DEVELOPER,
        )
        assert result.allowed is True
        assert result.remaining == 29  # Developer has 30/min limit

    @pytest.mark.asyncio
    async def test_decrements_remaining(self, rate_limiter):
        """Test that remaining count decrements correctly."""
        # First request
        result1 = await rate_limiter.check_and_increment(
            user_id="user_1",
            tier=UserTier.DEVELOPER,
        )
        assert result1.remaining == 29

        # Second request
        result2 = await rate_limiter.check_and_increment(
            user_id="user_1",
            tier=UserTier.DEVELOPER,
        )
        assert result2.remaining == 28

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self, rate_limiter):
        """Test that requests over limit are blocked."""
        # Free tier has 10/min limit
        for i in range(10):
            result = await rate_limiter.check_and_increment(
                user_id="user_free",
                tier=UserTier.FREE,
            )
            assert result.allowed is True

        # 11th request should be blocked
        result = await rate_limiter.check_and_increment(
            user_id="user_free",
            tier=UserTier.FREE,
        )
        assert result.allowed is False
        assert result.remaining == 0

    @pytest.mark.asyncio
    async def test_different_users_separate_limits(self, rate_limiter):
        """Test that different users have separate rate limits."""
        # Exhaust user 1's limit
        for _ in range(10):
            await rate_limiter.check_and_increment(
                user_id="user_1",
                tier=UserTier.FREE,
            )

        # User 1 is now rate limited
        result1 = await rate_limiter.check_and_increment(
            user_id="user_1",
            tier=UserTier.FREE,
        )
        assert result1.allowed is False

        # User 2 should still be allowed
        result2 = await rate_limiter.check_and_increment(
            user_id="user_2",
            tier=UserTier.FREE,
        )
        assert result2.allowed is True

    @pytest.mark.asyncio
    async def test_tier_limits_applied(self, rate_limiter):
        """Test that tier-specific limits are applied."""
        # Free: 10/min
        # Developer: 30/min
        # Pro: 100/min
        # Enterprise: 1000/min

        result_free = await rate_limiter.check_and_increment(
            user_id="user_free",
            tier=UserTier.FREE,
        )
        assert result_free.limit == 10

        result_dev = await rate_limiter.check_and_increment(
            user_id="user_dev",
            tier=UserTier.DEVELOPER,
        )
        assert result_dev.limit == 30

        result_pro = await rate_limiter.check_and_increment(
            user_id="user_pro",
            tier=UserTier.PRO,
        )
        assert result_pro.limit == 100

        result_ent = await rate_limiter.check_and_increment(
            user_id="user_ent",
            tier=UserTier.ENTERPRISE,
        )
        assert result_ent.limit == 1000

    @pytest.mark.asyncio
    async def test_retry_after_calculated(self, rate_limiter):
        """Test that retry_after is calculated correctly."""
        # Exhaust limit
        for _ in range(10):
            await rate_limiter.check_and_increment(
                user_id="user_free",
                tier=UserTier.FREE,
            )

        result = await rate_limiter.check_and_increment(
            user_id="user_free",
            tier=UserTier.FREE,
        )
        assert result.retry_after >= 0
        assert result.retry_after <= 60  # Window is 60 seconds

    @pytest.mark.asyncio
    async def test_get_current_usage_without_increment(self, rate_limiter):
        """Test getting current usage without incrementing."""
        # Make some requests
        for _ in range(5):
            await rate_limiter.check_and_increment(
                user_id="user_1",
                tier=UserTier.DEVELOPER,
            )

        # Check current usage
        result = await rate_limiter.get_current_usage(
            user_id="user_1",
            tier=UserTier.DEVELOPER,
        )
        assert result.remaining == 25  # 30 - 5

        # Should still be 25 (not incremented)
        result2 = await rate_limiter.get_current_usage(
            user_id="user_1",
            tier=UserTier.DEVELOPER,
        )
        assert result2.remaining == 25
