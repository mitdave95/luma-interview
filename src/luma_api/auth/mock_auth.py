"""Mock authentication service for development and testing."""

from datetime import datetime

from luma_api.config import UserTier
from luma_api.errors.exceptions import InvalidAPIKeyError
from luma_api.models.user import User

# Hardcoded test users for each tier
MOCK_USERS: dict[str, User] = {
    "free_test_key": User(
        id="user_free_001",
        email="free@test.com",
        tier=UserTier.FREE,
        api_key="free_test_key",
        created_at=datetime(2024, 1, 1),
    ),
    "dev_test_key": User(
        id="user_dev_001",
        email="developer@test.com",
        tier=UserTier.DEVELOPER,
        api_key="dev_test_key",
        created_at=datetime(2024, 1, 1),
    ),
    "pro_test_key": User(
        id="user_pro_001",
        email="pro@test.com",
        tier=UserTier.PRO,
        api_key="pro_test_key",
        created_at=datetime(2024, 1, 1),
    ),
    "enterprise_test_key": User(
        id="user_ent_001",
        email="enterprise@test.com",
        tier=UserTier.ENTERPRISE,
        api_key="enterprise_test_key",
        created_at=datetime(2024, 1, 1),
    ),
}


class MockAuthService:
    """Mock authentication service using hardcoded users."""

    def __init__(self, users: dict[str, User] | None = None):
        self._users = users or MOCK_USERS

    def validate_api_key(self, api_key: str) -> User:
        """
        Validate an API key and return the associated user.

        Args:
            api_key: The API key to validate

        Returns:
            The user associated with the API key

        Raises:
            InvalidAPIKeyError: If the API key is invalid
        """
        user = self._users.get(api_key)
        if user is None:
            raise InvalidAPIKeyError()

        if not user.is_active:
            raise InvalidAPIKeyError(message="User account is deactivated")

        return user

    def get_user_by_id(self, user_id: str) -> User | None:
        """Get a user by their ID."""
        for user in self._users.values():
            if user.id == user_id:
                return user
        return None

    def add_user(self, user: User) -> None:
        """Add a user (for testing)."""
        self._users[user.api_key] = user

    def remove_user(self, api_key: str) -> bool:
        """Remove a user (for testing)."""
        if api_key in self._users:
            del self._users[api_key]
            return True
        return False


# Global instance
_auth_service: MockAuthService | None = None


def get_auth_service() -> MockAuthService:
    """Get the auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = MockAuthService()
    return _auth_service


def reset_auth_service() -> None:
    """Reset the auth service (for testing)."""
    global _auth_service
    _auth_service = None
