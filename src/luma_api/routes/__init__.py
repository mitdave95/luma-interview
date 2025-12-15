"""API routes module."""

from luma_api.routes.account import router as account_router
from luma_api.routes.admin import router as admin_router
from luma_api.routes.generate import router as generate_router
from luma_api.routes.health import router as health_router
from luma_api.routes.jobs import router as jobs_router
from luma_api.routes.videos import router as videos_router
from luma_api.routes.websocket import router as websocket_router

__all__ = [
    "account_router",
    "admin_router",
    "generate_router",
    "health_router",
    "jobs_router",
    "videos_router",
    "websocket_router",
]
