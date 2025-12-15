"""Rate limiting middleware."""

import logging
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from luma_api.auth.mock_auth import get_auth_service
from luma_api.config import get_settings
from luma_api.errors.exceptions import TooManyRequestsError
from luma_api.models.responses import ErrorDetail, ErrorResponse
from luma_api.services.rate_limit_service import RateLimitResult, get_rate_limit_service
from luma_api.storage.redis_client import get_redis

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limits on API requests.

    Adds rate limit headers to all responses and blocks requests
    that exceed the user's tier-based rate limit.
    """

    # Paths to exclude from rate limiting
    EXCLUDED_PATHS = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    def __init__(self, app: FastAPI):
        super().__init__(app)
        self._settings = get_settings()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Add request ID to state
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Skip rate limiting for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        # Skip if rate limiting is disabled
        if not self._settings.rate_limit_enabled:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        # Try to get user from API key
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            # No API key - let the auth dependency handle it
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        # Validate user
        auth_service = get_auth_service()
        try:
            user = auth_service.validate_api_key(api_key)
        except Exception:
            # Invalid API key - let the endpoint handle the error
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        # Get rate limit service
        redis = await get_redis()
        rate_limit_service = get_rate_limit_service(redis)

        # Check rate limit
        result = await rate_limit_service.check_and_increment(
            user_id=user.id,
            tier=user.tier,
            endpoint=request.url.path,
        )

        if not result.allowed:
            # Rate limited
            logger.warning(
                "Rate limit exceeded for user %s on %s",
                user.id,
                request.url.path,
                extra={"request_id": request_id},
            )

            error = TooManyRequestsError(
                limit=result.limit,
                window_seconds=result.window_seconds,
                retry_after=result.retry_after,
                tier=user.tier.value,
            )

            error_detail = ErrorDetail(
                code=error.error_code,
                message=error.message,
                details=error.details,
                request_id=request_id,
            )
            error_response = ErrorResponse(error=error_detail)

            response = JSONResponse(
                status_code=429,
                content=error_response.model_dump(mode="json"),
            )
            self._add_rate_limit_headers(response, result, request_id)
            response.headers["Retry-After"] = str(result.retry_after)
            return response

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        self._add_rate_limit_headers(response, result, request_id)

        return response

    def _add_rate_limit_headers(
        self,
        response: Response,
        result: RateLimitResult,
        request_id: str,
    ) -> None:
        """Add rate limit headers to response."""
        response.headers["X-Request-ID"] = request_id
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(result.reset_at)
        response.headers["X-RateLimit-Window"] = str(result.window_seconds)
        response.headers["X-RateLimit-Policy"] = "sliding-window"
