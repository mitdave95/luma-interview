"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from luma_api import __version__
from luma_api.config import get_settings
from luma_api.errors.handlers import register_exception_handlers
from luma_api.middleware.rate_limiter import RateLimitMiddleware
from luma_api.queue.lua_scripts import lua_scripts
from luma_api.queue.worker import get_worker
from luma_api.routes import (
    account_router,
    admin_router,
    generate_router,
    health_router,
    jobs_router,
    scrape_router,
    videos_router,
    websocket_router,
)
from luma_api.storage.redis_client import (
    close_redis,
    get_redis,
    init_redis,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan handler.

    Handles startup and shutdown events:
    - Startup: Initialize Redis, load Lua scripts, start worker
    - Shutdown: Stop worker, close Redis connection
    """
    settings = get_settings()
    logger.info("Starting Luma API v%s in %s mode", __version__, settings.api_env.value)

    # Initialize Redis
    try:
        await init_redis()
        redis = await get_redis()
        if redis:
            await lua_scripts.load(redis)
            logger.info("Loaded Lua scripts into Redis")
    except Exception as e:
        logger.warning("Redis initialization failed: %s", e)

    # Start background worker
    worker = get_worker()
    await worker.start()

    yield

    # Shutdown
    logger.info("Shutting down Luma API")

    # Stop worker
    await worker.stop()

    # Close Redis
    await close_redis()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Luma Labs Enterprise API",
        description=(
            "Enterprise-grade API for Luma Labs AI text-to-video generation.\n\n"
            "## Features\n"
            "- Tiered user access (Free, Developer, Pro, Enterprise)\n"
            "- Rate limiting with sliding window algorithm\n"
            "- Priority queue with weighted fair queuing\n"
            "- Comprehensive error handling\n\n"
            "## Authentication\n"
            "All endpoints require an API key in the `X-API-Key` header.\n\n"
            "**Test API Keys:**\n"
            "- `free_test_key` - Free tier (read-only)\n"
            "- `dev_test_key` - Developer tier\n"
            "- `pro_test_key` - Pro tier\n"
            "- `enterprise_test_key` - Enterprise tier"
        ),
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "X-RateLimit-Window",
            "X-RateLimit-Policy",
            "X-Request-ID",
            "Retry-After",
        ],
    )

    # Add rate limiting middleware
    app.add_middleware(RateLimitMiddleware)  # type: ignore[arg-type]

    # Register exception handlers
    register_exception_handlers(app)

    # Include routers
    app.include_router(health_router)
    app.include_router(videos_router, prefix=settings.api_prefix)
    app.include_router(generate_router, prefix=settings.api_prefix)
    app.include_router(jobs_router, prefix=settings.api_prefix)
    app.include_router(account_router, prefix=settings.api_prefix)
    app.include_router(admin_router, prefix=settings.api_prefix)
    app.include_router(scrape_router, prefix=settings.api_prefix)
    app.include_router(websocket_router)  # WebSocket at root level

    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "luma_api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_env.value == "development",
    )
