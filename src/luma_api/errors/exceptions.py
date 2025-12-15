"""Custom exception hierarchy for the Luma API."""

from typing import Any

from luma_api.config import UserTier


class LumaAPIError(Exception):
    """Base exception for all Luma API errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An internal error occurred"

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message or self.__class__.message
        self.details = details or {}
        super().__init__(self.message)


# Authentication Errors (401)


class AuthenticationError(LumaAPIError):
    """Base authentication error."""

    status_code = 401
    error_code = "AUTH_ERROR"
    message = "Authentication failed"


class InvalidAPIKeyError(AuthenticationError):
    """Invalid or malformed API key."""

    error_code = "AUTH_INVALID_KEY"
    message = "Invalid API key provided"


class ExpiredTokenError(AuthenticationError):
    """Token has expired."""

    error_code = "AUTH_TOKEN_EXPIRED"
    message = "Authentication token has expired"


class MissingCredentialsError(AuthenticationError):
    """No credentials provided."""

    error_code = "AUTH_MISSING_CREDENTIALS"
    message = "No authentication credentials provided"


# Authorization Errors (403)


class AuthorizationError(LumaAPIError):
    """Base authorization error."""

    status_code = 403
    error_code = "AUTH_FORBIDDEN"
    message = "Access denied"


class InsufficientTierError(AuthorizationError):
    """User tier is insufficient for this operation."""

    error_code = "AUTH_INSUFFICIENT_TIER"
    message = "Your subscription tier does not allow this operation"

    def __init__(
        self,
        current_tier: UserTier,
        required_tier: UserTier,
        details: dict[str, Any] | None = None,
    ):
        base_details = {
            "current_tier": current_tier.value,
            "required_tier": required_tier.value,
            "upgrade_url": "https://lumalabs.ai/pricing",
        }
        if details:
            base_details.update(details)
        super().__init__(
            message=f"This operation requires {required_tier.value} tier or higher",
            details=base_details,
        )


class PermissionDeniedError(AuthorizationError):
    """User doesn't have permission for this resource."""

    error_code = "AUTH_PERMISSION_DENIED"
    message = "You don't have permission to access this resource"


class QuotaExceededError(AuthorizationError):
    """User has exceeded their quota."""

    status_code = 429
    error_code = "QUOTA_EXCEEDED"
    message = "You have exceeded your quota"

    def __init__(
        self,
        quota_type: str,
        limit: int,
        used: int,
        reset_at: str | None = None,
    ):
        details = {
            "quota_type": quota_type,
            "limit": limit,
            "used": used,
            "upgrade_url": "https://lumalabs.ai/pricing",
        }
        if reset_at:
            details["reset_at"] = reset_at
        super().__init__(
            message=f"{quota_type} quota exceeded ({used}/{limit})",
            details=details,
        )


# Rate Limit Errors (429)


class RateLimitError(LumaAPIError):
    """Base rate limit error."""

    status_code = 429
    error_code = "RATE_LIMITED"
    message = "Rate limit exceeded"


class TooManyRequestsError(RateLimitError):
    """Too many requests in time window."""

    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Rate limit exceeded for your tier"

    def __init__(
        self,
        limit: int,
        window_seconds: int,
        retry_after: int,
        tier: str,
    ):
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window_seconds}s",
            details={
                "limit": limit,
                "window": f"{window_seconds}s",
                "retry_after": retry_after,
                "tier": tier,
                "upgrade_url": "https://lumalabs.ai/pricing",
            },
        )
        self.retry_after = retry_after


# Validation Errors (400)


class ValidationError(LumaAPIError):
    """Base validation error."""

    status_code = 400
    error_code = "VALIDATION_ERROR"
    message = "Validation failed"


class InvalidPromptError(ValidationError):
    """Invalid prompt content."""

    error_code = "INVALID_PROMPT"
    message = "The prompt is invalid"


class InvalidParametersError(ValidationError):
    """Invalid request parameters."""

    error_code = "INVALID_PARAMETERS"
    message = "Invalid request parameters"


# Queue Errors


class QueueError(LumaAPIError):
    """Base queue error."""

    status_code = 503
    error_code = "QUEUE_ERROR"
    message = "Queue operation failed"


class QueueFullError(QueueError):
    """Queue is at capacity."""

    error_code = "QUEUE_FULL"
    message = "The processing queue is full, please try again later"


class JobNotFoundError(LumaAPIError):
    """Job not found."""

    status_code = 404
    error_code = "JOB_NOT_FOUND"
    message = "Job not found"

    def __init__(self, job_id: str):
        super().__init__(
            message=f"Job '{job_id}' not found",
            details={"job_id": job_id},
        )


class JobCancelledError(LumaAPIError):
    """Job was cancelled."""

    status_code = 409
    error_code = "JOB_CANCELLED"
    message = "Job has been cancelled"


# Generation Errors


class GenerationError(LumaAPIError):
    """Base generation error."""

    status_code = 500
    error_code = "GENERATION_ERROR"
    message = "Video generation failed"


class ModelUnavailableError(GenerationError):
    """Model is not available."""

    status_code = 503
    error_code = "MODEL_UNAVAILABLE"
    message = "The requested model is currently unavailable"


class ContentPolicyViolationError(GenerationError):
    """Content policy violation."""

    status_code = 422
    error_code = "CONTENT_POLICY_VIOLATION"
    message = "The request violates our content policy"


class GenerationTimeoutError(GenerationError):
    """Generation timed out."""

    status_code = 504
    error_code = "GENERATION_TIMEOUT"
    message = "Video generation timed out"


# Resource Not Found Errors (404)


class VideoNotFoundError(LumaAPIError):
    """Video not found."""

    status_code = 404
    error_code = "VIDEO_NOT_FOUND"
    message = "Video not found"

    def __init__(self, video_id: str):
        super().__init__(
            message=f"Video '{video_id}' not found",
            details={"video_id": video_id},
        )


# Internal Errors (500)


class InternalError(LumaAPIError):
    """Base internal error."""

    status_code = 500
    error_code = "INTERNAL_ERROR"
    message = "An internal error occurred"
