"""Video generation endpoints."""


from fastapi import APIRouter, Depends, status

from luma_api.auth.dependencies import require_tier
from luma_api.config import UserTier
from luma_api.models.generation import (
    BatchGenerationRequest,
    BatchGenerationResponse,
    GenerationRequest,
)
from luma_api.models.job import JobResponse
from luma_api.models.user import User
from luma_api.services.job_service import JobService, get_job_service

router = APIRouter(prefix="/generate", tags=["Generation"])


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate Video",
    description="Create a video generation job from a text prompt.",
)
async def generate_video(
    request: GenerationRequest,
    user: User = Depends(require_tier(UserTier.DEVELOPER)),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    """
    Create a video generation job.

    This endpoint queues a video generation request and returns immediately
    with a job ID that can be used to track progress.

    **Requirements:**
    - Developer tier or higher
    - Video duration must be within tier limits

    **Process:**
    1. Request is validated
    2. Job is created and added to the priority queue
    3. Job ID is returned for tracking
    4. Worker processes the job asynchronously
    5. Poll `/jobs/{job_id}` for status updates

    **Tier Limits:**
    - Developer: Max 30 seconds
    - Pro: Max 120 seconds
    - Enterprise: Max 300 seconds
    """
    job = await job_service.create_job(request, user)
    return JobResponse.from_job(job)


@router.post(
    "/batch",
    response_model=BatchGenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Batch Generate Videos",
    description="Create multiple video generation jobs at once.",
)
async def batch_generate_videos(
    request: BatchGenerationRequest,
    user: User = Depends(require_tier(UserTier.PRO)),
    job_service: JobService = Depends(get_job_service),
) -> BatchGenerationResponse:
    """
    Create multiple video generation jobs in a single request.

    **Requirements:**
    - Pro tier or higher
    - Maximum 10 requests per batch

    Returns a list of job IDs for tracking each video.
    Jobs are queued in order and processed based on priority.
    """
    job_ids: list[str] = []

    for gen_request in request.requests:
        job = await job_service.create_job(gen_request, user)
        job_ids.append(job.id)

    return BatchGenerationResponse(
        job_ids=job_ids,
        total_queued=len(job_ids),
    )


@router.get(
    "/models",
    summary="List Models",
    description="List available video generation models.",
)
async def list_models(
    user: User = Depends(require_tier(UserTier.FREE)),
):
    """
    List available video generation models.

    Returns information about each model including capabilities
    and recommended use cases.
    """
    # Mock model data
    return {
        "models": [
            {
                "id": "dream-machine-1.5",
                "name": "Dream Machine 1.5",
                "description": "Latest generation model with improved quality and coherence",
                "max_duration": 300,
                "supported_resolutions": ["480p", "720p", "1080p", "4k"],
                "supported_styles": [
                    "cinematic",
                    "anime",
                    "realistic",
                    "artistic",
                    "documentary",
                ],
                "default": True,
            },
            {
                "id": "dream-machine-1.0",
                "name": "Dream Machine 1.0",
                "description": "Original Dream Machine model",
                "max_duration": 120,
                "supported_resolutions": ["480p", "720p", "1080p"],
                "supported_styles": ["cinematic", "realistic"],
                "default": False,
            },
        ]
    }
