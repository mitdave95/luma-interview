"""Health check endpoint."""

from fastapi import APIRouter

from luma_api import __version__
from luma_api.models.responses import HealthResponse
from luma_api.storage.redis_client import RedisManager

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check the health status of the API and its dependencies.",
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns the health status of the API and its components:
    - API status
    - Redis connection status
    - Database status (mock)
    """
    components = {}

    # Check API (always up if we can respond)
    components["api"] = {"status": "up", "latency_ms": 0}

    # Check Redis
    redis_manager = RedisManager.get_instance()
    redis_health = await redis_manager.health_check()
    components["redis"] = redis_health

    # Mock database is always "up"
    components["database"] = {"status": "up", "latency_ms": 0, "type": "in-memory"}

    # Overall status
    all_up = all(
        c.get("status") == "up" or c.get("status") == "disconnected" for c in components.values()
    )
    status = "healthy" if all_up else "degraded"

    return HealthResponse(
        status=status,
        version=__version__,
        components=components,
    )


@router.get(
    "/",
    summary="Root",
    description="API root endpoint with basic info.",
)
async def root() -> dict[str, str]:
    """Root endpoint with API info."""
    return {
        "name": "Luma Labs Enterprise API",
        "version": __version__,
        "documentation": "/docs",
        "health": "/health",
    }
