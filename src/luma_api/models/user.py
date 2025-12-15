"""User models."""

from datetime import UTC, datetime

from pydantic import BaseModel, EmailStr, Field

from luma_api.config import UserTier


class User(BaseModel):
    """User model."""

    id: str = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User email address")
    tier: UserTier = Field(..., description="User subscription tier")
    api_key: str = Field(..., description="User API key")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_active: bool = Field(default=True)
    metadata: dict | None = Field(default=None)

    model_config = {"from_attributes": True}
