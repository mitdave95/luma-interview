"""WebSocket endpoint for real-time dashboard updates."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from luma_api.auth.mock_auth import MOCK_USERS
from luma_api.models.job import JobStatus
from luma_api.services.queue_service import get_queue_service
from luma_api.services.rate_limit_service import get_rate_limit_service
from luma_api.storage.memory import get_storage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


class DashboardConnectionManager:
    """Manage WebSocket connections for the dashboard."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self._recent_requests: list[dict[str, Any]] = []
        self._max_recent_requests = 100

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and track a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Dashboard client connected. Total: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("Dashboard client disconnected. Total: %d", len(self.active_connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    def add_request(self, request_data: dict[str, Any]) -> None:
        """Add a request to the recent requests log."""
        self._recent_requests.insert(0, request_data)
        if len(self._recent_requests) > self._max_recent_requests:
            self._recent_requests = self._recent_requests[: self._max_recent_requests]

    def get_recent_requests(self) -> list[dict[str, Any]]:
        """Get the most recent requests."""
        return self._recent_requests.copy()


# Singleton connection manager
manager = DashboardConnectionManager()


def get_connection_manager() -> DashboardConnectionManager:
    """Get the connection manager instance."""
    return manager


async def get_dashboard_snapshot() -> dict[str, Any]:
    """Get a complete snapshot of the dashboard state."""
    queue_service = get_queue_service()
    rate_limit_service = get_rate_limit_service()
    storage = get_storage()

    # Get queue stats with job details
    queue_stats = await queue_service.get_queue_stats()
    all_queue_jobs = await queue_service.queue.get_queue_jobs_all()

    # Get rate limit status for all users
    rate_limits = {}
    for api_key, user in MOCK_USERS.items():
        result = await rate_limit_service.get_current_usage(
            user_id=user.id,
            tier=user.tier,
        )
        rate_limits[user.id] = {
            "user_id": user.id,
            "tier": user.tier.value,
            "limit": result.limit,
            "remaining": result.remaining,
            "reset_at": result.reset_at,
            "is_rate_limited": result.remaining == 0,
        }

    # Get all concurrent jobs (queued + processing)
    active_jobs = []
    jobs_list, _ = storage.jobs.list(
        filter_fn=lambda j: j.status in (JobStatus.QUEUED, JobStatus.PROCESSING),
        sort_key="created_at",
        sort_desc=True,
    )
    for job in jobs_list[:50]:  # Limit to 50 jobs
        active_jobs.append(
            {
                "job_id": job.id,
                "user_id": job.user_id,
                "status": job.status.value,
                "priority": job.priority.value,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "progress": job.progress,
                "prompt": job.prompt[:50] + "..." if len(job.prompt) > 50 else job.prompt,
            }
        )

    return {
        "queues": {
            "critical": {
                "length": queue_stats["queues"].get("critical", {}).get("length", 0),
                "weight": 10,
                "jobs": all_queue_jobs.get("critical", []),
            },
            "high": {
                "length": queue_stats["queues"].get("high", {}).get("length", 0),
                "weight": 5,
                "jobs": all_queue_jobs.get("high", []),
            },
            "normal": {
                "length": queue_stats["queues"].get("normal", {}).get("length", 0),
                "weight": 1,
                "jobs": all_queue_jobs.get("normal", []),
            },
        },
        "total_queued": queue_stats["total_jobs"],
        "rate_limits": rate_limits,
        "active_jobs": active_jobs,
        "recent_requests": manager.get_recent_requests(),
    }


@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time dashboard updates.

    Sends periodic updates with:
    - Queue state (jobs per priority level)
    - Rate limit status for all users
    - Active jobs being processed
    - Recent request log
    """
    await manager.connect(websocket)

    try:
        # Send initial connected message
        await websocket.send_json(
            {
                "type": "connected",
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        # Send initial state
        initial_state = await get_dashboard_snapshot()
        await websocket.send_json(
            {
                "type": "update",
                "data": initial_state,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        # Periodic updates loop
        while True:
            await asyncio.sleep(1)  # Update every second

            try:
                dashboard_data = await get_dashboard_snapshot()
                await websocket.send_json(
                    {
                        "type": "update",
                        "data": dashboard_data,
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                )
            except WebSocketDisconnect:
                # Client disconnected, exit the loop
                break
            except Exception as e:
                # Connection error (e.g., close message sent), exit the loop
                logger.debug("WebSocket send failed, closing: %s", e)
                break

    except WebSocketDisconnect:
        pass  # Normal disconnect
    except Exception as e:
        logger.warning("WebSocket error: %s", e)
    finally:
        manager.disconnect(websocket)
