"""Redis client management."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from luma_api.config import get_settings

logger = logging.getLogger(__name__)


class RedisManager:
    """Manages Redis connection pool."""

    _instance: Optional["RedisManager"] = None
    _redis: Redis | None = None

    def __init__(self) -> None:
        self._settings = get_settings()
        self._pool: redis.ConnectionPool | None = None

    @classmethod
    def get_instance(cls) -> "RedisManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def connect(self) -> None:
        """Initialize Redis connection pool."""
        if self._redis is not None:
            return

        try:
            self._pool = redis.ConnectionPool.from_url(
                self._settings.redis_url,
                max_connections=self._settings.redis_max_connections,
                decode_responses=True,
            )
            self._redis = Redis(connection_pool=self._pool)

            # Test connection
            await self._redis.ping()  # type: ignore[misc]
            logger.info("Connected to Redis at %s", self._settings.redis_url)
        except Exception as e:
            logger.error("Failed to connect to Redis: %s", e)
            self._redis = None
            raise

    async def disconnect(self) -> None:
        """Close Redis connection pool."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None
            logger.info("Disconnected from Redis")

        if self._pool:
            await self._pool.disconnect()
            self._pool = None

    @property
    def client(self) -> Redis | None:
        """Get Redis client instance."""
        return self._redis

    async def health_check(self) -> dict[str, Any]:
        """Check Redis health."""
        if self._redis is None:
            return {"status": "disconnected", "latency_ms": None}

        try:
            import time

            start = time.perf_counter()
            await self._redis.ping()  # type: ignore[misc]
            latency = (time.perf_counter() - start) * 1000

            return {"status": "up", "latency_ms": round(latency, 2)}
        except Exception as e:
            return {"status": "error", "error": str(e), "latency_ms": None}

    @classmethod
    async def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        if cls._instance:
            await cls._instance.disconnect()
        cls._instance = None


@asynccontextmanager
async def get_redis_context() -> AsyncGenerator[Redis | None, None]:
    """Context manager for Redis operations with fallback."""
    manager = RedisManager.get_instance()
    try:
        if manager.client is None:
            await manager.connect()
        yield manager.client
    except redis.RedisError as e:
        logger.warning("Redis operation failed: %s", e)
        yield None


async def get_redis() -> Redis | None:
    """Dependency to get Redis client."""
    manager = RedisManager.get_instance()
    return manager.client


async def init_redis() -> None:
    """Initialize Redis connection (call at startup)."""
    manager = RedisManager.get_instance()
    try:
        await manager.connect()
    except Exception as e:
        logger.warning("Redis not available, rate limiting will be disabled: %s", e)


async def close_redis() -> None:
    """Close Redis connection (call at shutdown)."""
    await RedisManager.reset()
