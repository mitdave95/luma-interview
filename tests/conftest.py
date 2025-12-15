"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from luma_api.auth.mock_auth import MOCK_USERS, reset_auth_service
from luma_api.main import create_app
from luma_api.queue.priority_queue import reset_priority_queue
from luma_api.queue.worker import reset_worker
from luma_api.services.account_service import reset_account_service
from luma_api.services.job_service import reset_job_service
from luma_api.services.queue_service import reset_queue_service
from luma_api.services.rate_limit_service import reset_rate_limit_service
from luma_api.services.video_service import reset_video_service
from luma_api.storage.memory import StorageManager


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def reset_singletons():
    """Reset all singleton services before each test."""
    # Reset storage
    StorageManager.reset()

    # Reset services
    reset_auth_service()
    reset_rate_limit_service()
    reset_queue_service()
    reset_priority_queue()
    reset_job_service()
    reset_video_service()
    reset_account_service()
    reset_worker()

    yield

    # Cleanup after test
    StorageManager.reset()


@pytest.fixture
def app(reset_singletons):
    """Create FastAPI app for testing."""
    return create_app()


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    """Create test client."""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        # Clear Redis rate limit keys if Redis is connected
        try:
            import redis

            r = redis.from_url("redis://localhost:6379/0")
            # Delete all rate limit keys
            for key in r.scan_iter("rate_limit:*"):
                r.delete(key)
            # Delete all queue keys
            for key in r.scan_iter("queue:*"):
                r.delete(key)
            r.close()
        except Exception:
            pass  # Redis not available, that's fine
        yield test_client


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.eval = AsyncMock(return_value=[1, 9, 1700000000])
    redis.evalsha = AsyncMock(return_value=[1, 9, 1700000000])
    redis.zadd = AsyncMock(return_value=1)
    redis.zrank = AsyncMock(return_value=0)
    redis.zcard = AsyncMock(return_value=0)
    redis.zrem = AsyncMock(return_value=1)
    redis.zrange = AsyncMock(return_value=[])
    redis.zremrangebyscore = AsyncMock(return_value=0)
    redis.script_load = AsyncMock(return_value="sha256hash")
    return redis


# API Key fixtures for each tier
@pytest.fixture
def free_user_headers():
    """Headers for free tier user."""
    return {"X-API-Key": "free_test_key"}


@pytest.fixture
def dev_user_headers():
    """Headers for developer tier user."""
    return {"X-API-Key": "dev_test_key"}


@pytest.fixture
def pro_user_headers():
    """Headers for pro tier user."""
    return {"X-API-Key": "pro_test_key"}


@pytest.fixture
def enterprise_user_headers():
    """Headers for enterprise tier user."""
    return {"X-API-Key": "enterprise_test_key"}


@pytest.fixture
def invalid_user_headers():
    """Headers with invalid API key."""
    return {"X-API-Key": "invalid_key"}


# User fixtures
@pytest.fixture
def free_user():
    """Get free tier user."""
    return MOCK_USERS["free_test_key"]


@pytest.fixture
def dev_user():
    """Get developer tier user."""
    return MOCK_USERS["dev_test_key"]


@pytest.fixture
def pro_user():
    """Get pro tier user."""
    return MOCK_USERS["pro_test_key"]


@pytest.fixture
def enterprise_user():
    """Get enterprise tier user."""
    return MOCK_USERS["enterprise_test_key"]


# Sample data fixtures
@pytest.fixture
def sample_generation_request():
    """Sample video generation request."""
    return {
        "prompt": "A beautiful sunset over the ocean with seagulls flying",
        "duration": 10,
        "resolution": "1080p",
        "aspect_ratio": "16:9",
    }


@pytest.fixture
def sample_batch_request():
    """Sample batch generation request."""
    return {
        "requests": [
            {"prompt": "A cat playing piano", "duration": 5},
            {"prompt": "A dog skateboarding", "duration": 5},
        ]
    }
