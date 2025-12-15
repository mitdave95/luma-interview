"""In-memory storage implementation."""

import builtins
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class InMemoryStorage(Generic[T]):
    """Generic in-memory storage using dictionaries."""

    def __init__(self, id_field: str = "id"):
        self._store: dict[str, T] = {}
        self._id_field = id_field

    def get(self, id: str) -> T | None:
        """Get an item by ID."""
        return self._store.get(id)

    def list(
        self,
        offset: int = 0,
        limit: int = 20,
        filter_fn: Callable[[T], bool] | None = None,
        sort_key: str | None = None,
        sort_desc: bool = True,
    ) -> tuple[list[T], int]:
        """
        List items with pagination and optional filtering.

        Returns:
            Tuple of (items, total_count)
        """
        items = list(self._store.values())

        # Apply filter
        if filter_fn:
            items = [item for item in items if filter_fn(item)]

        total = len(items)

        # Sort
        if sort_key:
            items.sort(
                key=lambda x: getattr(x, sort_key, datetime.min),
                reverse=sort_desc,
            )

        # Paginate
        items = items[offset : offset + limit]

        return items, total

    def create(self, item: T) -> T:
        """Create a new item."""
        item_id = getattr(item, self._id_field)
        self._store[item_id] = item
        return item

    def update(self, id: str, item: T) -> T | None:
        """Update an existing item."""
        if id not in self._store:
            return None
        self._store[id] = item
        return item

    def delete(self, id: str) -> bool:
        """Delete an item by ID."""
        if id in self._store:
            del self._store[id]
            return True
        return False

    def exists(self, id: str) -> bool:
        """Check if an item exists."""
        return id in self._store

    def count(self, filter_fn: Callable[[T], bool] | None = None) -> int:
        """Count items, optionally filtered."""
        if filter_fn:
            return sum(1 for item in self._store.values() if filter_fn(item))
        return len(self._store)

    def clear(self) -> None:
        """Clear all items."""
        self._store.clear()

    def find_one(self, filter_fn: Callable[[T], bool]) -> T | None:
        """Find a single item matching the filter."""
        for item in self._store.values():
            if filter_fn(item):
                return item
        return None

    def find_many(self, filter_fn: Callable[[T], bool]) -> builtins.list[T]:
        """Find all items matching the filter."""
        return [item for item in self._store.values() if filter_fn(item)]


class UsageCounter:
    """Track usage counts with time-based keys."""

    def __init__(self):
        self._daily: dict[str, int] = {}  # key: "user_id:YYYY-MM-DD"
        self._monthly: dict[str, int] = {}  # key: "user_id:YYYY-MM"

    def _get_daily_key(self, user_id: str, date: datetime | None = None) -> str:
        date = date or datetime.now(UTC)
        return f"{user_id}:{date.strftime('%Y-%m-%d')}"

    def _get_monthly_key(self, user_id: str, date: datetime | None = None) -> str:
        date = date or datetime.now(UTC)
        return f"{user_id}:{date.strftime('%Y-%m')}"

    def increment_daily(self, user_id: str, amount: int = 1) -> int:
        """Increment daily count and return new value."""
        key = self._get_daily_key(user_id)
        self._daily[key] = self._daily.get(key, 0) + amount
        return self._daily[key]

    def increment_monthly(self, user_id: str, amount: int = 1) -> int:
        """Increment monthly count and return new value."""
        key = self._get_monthly_key(user_id)
        self._monthly[key] = self._monthly.get(key, 0) + amount
        return self._monthly[key]

    def get_daily(self, user_id: str, date: datetime | None = None) -> int:
        """Get daily count for a user."""
        key = self._get_daily_key(user_id, date)
        return self._daily.get(key, 0)

    def get_monthly(self, user_id: str, date: datetime | None = None) -> int:
        """Get monthly count for a user."""
        key = self._get_monthly_key(user_id, date)
        return self._monthly.get(key, 0)

    def clear(self) -> None:
        """Clear all counters."""
        self._daily.clear()
        self._monthly.clear()


class StorageManager:
    """Central manager for all in-memory storage."""

    _instance: Optional["StorageManager"] = None

    def __init__(self):
        from luma_api.models.job import Job
        from luma_api.models.user import User
        from luma_api.models.video import Video

        self.videos: InMemoryStorage[Video] = InMemoryStorage[Video]()
        self.jobs: InMemoryStorage[Job] = InMemoryStorage[Job]()
        self.users: InMemoryStorage[User] = InMemoryStorage[User]()
        self.usage = UsageCounter()
        self._usage_details: dict[str, dict[str, Any]] = {}

    @classmethod
    def get_instance(cls) -> "StorageManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None

    def record_usage(
        self,
        user_id: str,
        videos_generated: int = 0,
        duration_seconds: float = 0,
    ) -> None:
        """Record usage statistics for a user."""
        self.usage.increment_daily(user_id)
        self.usage.increment_monthly(user_id)

        # Store detailed usage
        now = datetime.now(UTC)
        daily_key = f"{user_id}:{now.strftime('%Y-%m-%d')}"

        if daily_key not in self._usage_details:
            self._usage_details[daily_key] = {
                "videos_generated": 0,
                "total_duration_seconds": 0.0,
            }

        self._usage_details[daily_key]["videos_generated"] += videos_generated
        self._usage_details[daily_key]["total_duration_seconds"] += duration_seconds

    def get_usage_details(self, user_id: str, date: datetime | None = None) -> dict[str, Any]:
        """Get detailed usage for a user on a date."""
        date = date or datetime.now(UTC)
        daily_key = f"{user_id}:{date.strftime('%Y-%m-%d')}"
        return self._usage_details.get(
            daily_key,
            {"videos_generated": 0, "total_duration_seconds": 0.0},
        )


def get_storage() -> StorageManager:
    """Dependency to get storage manager."""
    return StorageManager.get_instance()
