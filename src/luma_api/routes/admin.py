"""Admin endpoints for dashboard data."""

from typing import Any

from fastapi import APIRouter

from luma_api.auth.mock_auth import MOCK_USERS
from luma_api.models.job import JobStatus
from luma_api.services.queue_service import get_queue_service
from luma_api.services.rate_limit_service import get_rate_limit_service
from luma_api.storage.memory import get_storage

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/dashboard",
    summary="Get Dashboard Data",
    description="Get all dashboard data in a single call.",
)
async def get_dashboard_data() -> dict[str, Any]:
    """
    Get comprehensive dashboard data including:
    - Queue statistics and jobs
    - Rate limit status for all users
    - Active jobs being processed
    """
    queue_service = get_queue_service()
    rate_limit_service = get_rate_limit_service()
    storage = get_storage()

    # Get queue stats
    queue_stats = await queue_service.get_queue_stats()
    all_queue_jobs = await queue_service.queue.get_queue_jobs_all()

    # Get rate limits for all mock users
    rate_limits = await rate_limit_service.get_all_user_limits()

    # Get active jobs
    active_jobs = []
    jobs_list, _ = storage.jobs.list(
        filter_fn=lambda j: j.status == JobStatus.PROCESSING,
        sort_key="started_at",
        sort_desc=True,
    )
    for job in jobs_list[:20]:
        active_jobs.append(
            {
                "job_id": job.id,
                "user_id": job.user_id,
                "priority": job.priority.value,
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
    }


@router.get(
    "/queue-stats",
    summary="Get Queue Statistics",
    description="Get detailed queue statistics including jobs in each queue.",
)
async def get_queue_stats() -> dict[str, Any]:
    """
    Get detailed queue statistics:
    - Length of each priority queue
    - List of jobs in each queue with metadata
    """
    queue_service = get_queue_service()
    storage = get_storage()

    queue_stats = await queue_service.get_queue_stats()
    all_queue_jobs = await queue_service.queue.get_queue_jobs_all()

    # Enrich job data with user info
    for priority, jobs in all_queue_jobs.items():
        for job_data in jobs:
            job = storage.jobs.get(job_data["job_id"])
            if job:
                job_data["user_id"] = job.user_id
                job_data["prompt"] = job.prompt[:30] + "..." if len(job.prompt) > 30 else job.prompt
                job_data["priority"] = job.priority.value

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
        "total_jobs": queue_stats["total_jobs"],
    }


@router.get(
    "/rate-limits",
    summary="Get Rate Limits",
    description="Get rate limit status for all users.",
)
async def get_rate_limits() -> dict[str, Any]:
    """
    Get rate limit status for all mock users:
    - Current usage vs limit
    - Whether each user is rate limited
    - Reset time
    """
    rate_limit_service = get_rate_limit_service()
    return await rate_limit_service.get_all_user_limits()


@router.get(
    "/active-jobs",
    summary="Get Active Jobs",
    description="Get jobs currently being processed.",
)
async def get_active_jobs() -> dict[str, Any]:
    """
    Get jobs currently being processed:
    - Job ID and user
    - Progress percentage
    - Started time
    """
    storage = get_storage()

    active_jobs = []
    jobs_list, total = storage.jobs.list(
        filter_fn=lambda j: j.status == JobStatus.PROCESSING,
        sort_key="started_at",
        sort_desc=True,
    )

    for job in jobs_list[:50]:  # Limit to 50
        active_jobs.append(
            {
                "job_id": job.id,
                "user_id": job.user_id,
                "priority": job.priority.value,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "progress": job.progress or 0,
                "prompt": job.prompt[:50] + "..." if len(job.prompt) > 50 else job.prompt,
                "duration": job.duration,
            }
        )

    return {
        "active_jobs": active_jobs,
        "total_active": total,
    }


@router.get(
    "/users",
    summary="Get Mock Users",
    description="Get list of available mock users for testing.",
)
async def get_mock_users() -> dict[str, Any]:
    """
    Get list of mock users available for API testing:
    - API keys
    - User tiers
    - Rate limits
    """
    from luma_api.config import get_tier_config

    users = []
    for api_key, user in MOCK_USERS.items():
        tier_config = get_tier_config(user.tier)
        users.append(
            {
                "api_key": api_key,
                "user_id": user.id,
                "email": user.email,
                "tier": user.tier.value,
                "rate_limit_per_minute": tier_config.rate_limit_per_minute,
                "daily_quota": tier_config.daily_quota,
                "can_generate": tier_config.can_generate,
                "can_batch_generate": tier_config.can_batch_generate,
                "max_video_duration": tier_config.max_video_duration,
            }
        )

    return {"users": users}
