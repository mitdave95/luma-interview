"""Job management endpoints."""


from fastapi import APIRouter, Depends, Query

from luma_api.auth.dependencies import get_current_user
from luma_api.models.job import JobResponse, JobStatus
from luma_api.models.responses import PaginatedResponse
from luma_api.models.user import User
from luma_api.services.job_service import JobService, get_job_service

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get(
    "",
    response_model=PaginatedResponse[JobResponse],
    summary="List Jobs",
    description="List all jobs for the authenticated user.",
)
async def list_jobs(
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status_filter: JobStatus | None = Query(
        default=None, alias="status", description="Filter by job status"
    ),
    user: User = Depends(get_current_user),
    job_service: JobService = Depends(get_job_service),
) -> PaginatedResponse[JobResponse]:
    """
    List jobs for the authenticated user.

    - Supports pagination with `page` and `per_page` parameters
    - Optional filtering by job status
    - Results are sorted by creation date (newest first)
    """
    jobs, total = job_service.list_jobs(
        user=user,
        page=page,
        per_page=per_page,
        status=status_filter,
    )

    # Convert to response format
    job_responses = [JobResponse.from_job(job) for job in jobs]

    return PaginatedResponse.create(
        items=job_responses,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get Job",
    description="Get the status and details of a specific job.",
)
async def get_job(
    job_id: str,
    user: User = Depends(get_current_user),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """
    Get job details by ID.

    Returns the current status of the job including:
    - Queue position (if queued)
    - Estimated wait time
    - Progress (if processing)
    - Result video ID (if completed)
    - Error message (if failed)
    """
    return job_service.get_job_response(job_id, user)


@router.delete(
    "/{job_id}",
    response_model=JobResponse,
    summary="Cancel Job",
    description="Cancel a pending or queued job.",
)
async def cancel_job(
    job_id: str,
    user: User = Depends(get_current_user),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """
    Cancel a job.

    Jobs can only be cancelled if they are in PENDING or QUEUED status.
    Jobs that are already PROCESSING, COMPLETED, FAILED, or CANCELLED
    cannot be cancelled.

    Returns the updated job with CANCELLED status.
    """
    job = await job_service.cancel_job(job_id, user)
    return JobResponse.from_job(job)
