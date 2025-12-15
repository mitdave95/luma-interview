"""FastAPI authentication dependencies."""

from collections.abc import Awaitable, Callable

from fastapi import Depends, Header

from luma_api.auth.mock_auth import MockAuthService, get_auth_service
from luma_api.config import UserTier, get_tier_config
from luma_api.errors.exceptions import (
    InsufficientTierError,
    MissingCredentialsError,
)
from luma_api.models.user import User


async def get_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    """Extract API key from header."""
    if x_api_key is None:
        raise MissingCredentialsError()
    return x_api_key


async def get_current_user(
    api_key: str = Depends(get_api_key),
    auth_service: MockAuthService = Depends(get_auth_service),
) -> User:
    """
    Get the current authenticated user.

    This dependency validates the API key and returns the associated user.
    """
    return auth_service.validate_api_key(api_key)


def require_tier(minimum_tier: UserTier) -> Callable[..., Awaitable[User]]:
    """
    Create a dependency that requires a minimum user tier.

    Usage:
        @router.post("/generate")
        async def generate(user: User = Depends(require_tier(UserTier.DEVELOPER))):
            ...
    """

    async def check_tier(user: User = Depends(get_current_user)) -> User:
        # Define tier hierarchy (higher index = higher tier)
        tier_hierarchy = [
            UserTier.FREE,
            UserTier.DEVELOPER,
            UserTier.PRO,
            UserTier.ENTERPRISE,
        ]

        user_tier_index = tier_hierarchy.index(user.tier)
        required_tier_index = tier_hierarchy.index(minimum_tier)

        if user_tier_index < required_tier_index:
            raise InsufficientTierError(user.tier, minimum_tier)

        return user

    return check_tier


async def get_optional_user(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    auth_service: MockAuthService = Depends(get_auth_service),
) -> User | None:
    """
    Get the current user if authenticated, otherwise return None.

    Useful for endpoints that work differently for authenticated vs anonymous users.
    """
    if x_api_key is None:
        return None

    try:
        return auth_service.validate_api_key(x_api_key)
    except Exception:
        return None


def require_permission(permission: str) -> Callable[..., Awaitable[User]]:
    """
    Create a dependency that requires a specific permission.

    This checks tier-based permissions from the tier config.
    """

    async def check_permission(user: User = Depends(get_current_user)) -> User:
        tier_config = get_tier_config(user.tier)

        # Check specific permissions
        permission_map = {
            "generate": tier_config.can_generate,
            "batch_generate": tier_config.can_batch_generate,
        }

        if permission in permission_map:
            if not permission_map[permission]:
                # Determine what tier is needed
                required_tier = UserTier.DEVELOPER
                if permission == "batch_generate":
                    required_tier = UserTier.PRO
                raise InsufficientTierError(user.tier, required_tier)

        return user

    return check_permission
