"""Account management endpoints."""

from fastapi import APIRouter, Depends, Query

from luma_api.auth.dependencies import get_current_user
from luma_api.models.responses import AccountResponse, QuotaResponse, UsageResponse
from luma_api.models.user import User
from luma_api.services.account_service import AccountService, get_account_service

router = APIRouter(prefix="/account", tags=["Account"])


@router.get(
    "",
    response_model=AccountResponse,
    summary="Get Account",
    description="Get account details for the authenticated user.",
)
async def get_account(
    user: User = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
) -> AccountResponse:
    """
    Get account details.

    Returns the user's account information including:
    - User ID
    - Email
    - Subscription tier
    - Account creation date
    - Account status
    """
    return account_service.get_account(user)


@router.get(
    "/usage",
    response_model=UsageResponse,
    summary="Get Usage",
    description="Get usage statistics for the authenticated user.",
)
async def get_usage(
    period: str = Query(
        default="daily",
        pattern="^(daily|monthly)$",
        description="Time period for usage stats",
    ),
    user: User = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
) -> UsageResponse:
    """
    Get usage statistics.

    Returns usage information for the specified period:
    - Number of API requests made
    - Number of videos generated
    - Total video duration generated
    - Period start and end times
    """
    return account_service.get_usage(user, period)


@router.get(
    "/quota",
    response_model=QuotaResponse,
    summary="Get Quota",
    description="Get quota information for the authenticated user.",
)
async def get_quota(
    user: User = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
) -> QuotaResponse:
    """
    Get quota information.

    Returns current quota status including:
    - Rate limit (requests per minute)
    - Daily quota (requests per day)
    - Concurrent job limit
    - Maximum video duration
    - Feature access (generate, batch generate)

    Use this endpoint to check limits before making requests.
    """
    return await account_service.get_quota(user)
