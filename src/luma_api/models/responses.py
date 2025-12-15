"""Standard API response models."""

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Detailed error information."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(default=None, description="Additional error details")
    request_id: str | None = Field(default=None, description="Request ID for tracking")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    documentation_url: str | None = Field(
        default=None, description="Link to documentation about this error"
    )


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: ErrorDetail


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number (1-indexed)")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: list[T] = Field(..., description="List of items")
    meta: PaginationMeta = Field(..., description="Pagination metadata")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        per_page: int,
    ) -> "PaginatedResponse[T]":
        """Create a paginated response."""
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        return cls(
            items=items,
            meta=PaginationMeta(
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
        )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="API version")
    components: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Component health status"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AccountResponse(BaseModel):
    """Account details response."""

    user_id: str
    email: str
    tier: str
    created_at: datetime
    is_active: bool


class UsageResponse(BaseModel):
    """Usage statistics response."""

    user_id: str
    tier: str
    period: str  # "daily" or "monthly"
    requests_made: int
    videos_generated: int
    total_duration_seconds: float
    period_start: datetime
    period_end: datetime


class QuotaResponse(BaseModel):
    """Quota information response."""

    user_id: str
    tier: str
    rate_limit: dict[str, Any] = Field(..., description="Rate limit info (limit, remaining, reset)")
    daily_quota: dict[str, Any] = Field(
        ..., description="Daily quota info (limit, used, remaining)"
    )
    concurrent_jobs: dict[str, Any] = Field(..., description="Concurrent job info (limit, active)")
    max_video_duration: int = Field(..., description="Maximum video duration in seconds")
    can_generate: bool
    can_batch_generate: bool
