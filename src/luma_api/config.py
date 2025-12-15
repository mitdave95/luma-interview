"""Application configuration and tier settings."""

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

from pydantic_settings import BaseSettings


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_env: Environment = Environment.DEVELOPMENT
    api_prefix: str = "/v1"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 100

    # Rate limiting
    rate_limit_enabled: bool = True

    # Worker
    worker_enabled: bool = True
    worker_poll_interval: float = 0.5

    model_config = {"env_prefix": "", "case_sensitive": False}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


class UserTier(str, Enum):
    """User subscription tiers."""

    FREE = "free"
    DEVELOPER = "developer"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass(frozen=True)
class TierConfig:
    """Configuration for a user tier."""

    rate_limit_per_minute: int
    daily_quota: int
    max_concurrent_jobs: int
    max_video_duration: int  # seconds
    queue_priority_weight: int
    can_generate: bool
    can_batch_generate: bool


TIER_CONFIGS: dict[UserTier, TierConfig] = {
    UserTier.FREE: TierConfig(
        rate_limit_per_minute=10,
        daily_quota=100,
        max_concurrent_jobs=0,
        max_video_duration=0,
        queue_priority_weight=0,
        can_generate=False,
        can_batch_generate=False,
    ),
    UserTier.DEVELOPER: TierConfig(
        rate_limit_per_minute=30,
        daily_quota=500,
        max_concurrent_jobs=3,
        max_video_duration=30,
        queue_priority_weight=1,
        can_generate=True,
        can_batch_generate=False,
    ),
    UserTier.PRO: TierConfig(
        rate_limit_per_minute=100,
        daily_quota=5000,
        max_concurrent_jobs=10,
        max_video_duration=120,
        queue_priority_weight=5,
        can_generate=True,
        can_batch_generate=True,
    ),
    UserTier.ENTERPRISE: TierConfig(
        rate_limit_per_minute=1000,
        daily_quota=-1,  # unlimited
        max_concurrent_jobs=100,
        max_video_duration=300,
        queue_priority_weight=10,
        can_generate=True,
        can_batch_generate=True,
    ),
}


def get_tier_config(tier: UserTier) -> TierConfig:
    """Get configuration for a user tier."""
    return TIER_CONFIGS[tier]
