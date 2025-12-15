"""FastAPI exception handlers."""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from luma_api.errors.exceptions import LumaAPIException, TooManyRequestsError
from luma_api.models.responses import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


def create_error_response(
    error_code: str,
    message: str,
    status_code: int,
    details: dict | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    """Create a standardized error response."""
    error_detail = ErrorDetail(
        code=error_code,
        message=message,
        details=details,
        request_id=request_id or str(uuid.uuid4()),
        timestamp=datetime.now(UTC),
        documentation_url=f"https://docs.lumalabs.ai/errors/{error_code}",
    )
    response = ErrorResponse(error=error_detail)
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(mode="json"),
    )


async def luma_exception_handler(
    request: Request,
    exc: LumaAPIException,
) -> JSONResponse:
    """Handle LumaAPIException and subclasses."""
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())

    logger.warning(
        "API error: %s - %s",
        exc.error_code,
        exc.message,
        extra={"request_id": request_id, "details": exc.details},
    )

    response = create_error_response(
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        request_id=request_id,
    )

    # Add Retry-After header for rate limit errors
    if isinstance(exc, TooManyRequestsError):
        response.headers["Retry-After"] = str(exc.retry_after)

    return response


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())

    # Format validation errors
    errors = []
    for error in exc.errors():
        loc = ".".join(str(x) for x in error["loc"])
        errors.append({"field": loc, "message": error["msg"], "type": error["type"]})

    logger.warning(
        "Validation error",
        extra={"request_id": request_id, "errors": errors},
    )

    return create_error_response(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        status_code=400,
        details={"errors": errors},
        request_id=request_id,
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected exceptions."""
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())

    logger.exception(
        "Unhandled exception",
        extra={"request_id": request_id},
    )

    return create_error_response(
        error_code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        status_code=500,
        request_id=request_id,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(LumaAPIException, luma_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
