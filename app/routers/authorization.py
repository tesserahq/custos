from fastapi import APIRouter
from app.schemas.authorization import (
    AuthorizationRequest,
    AuthorizationResponse,
)
from app.services.casbin_service import get_casbin_service
from app.core.logging_config import get_logger

router = APIRouter(prefix="/authorization", tags=["authorization"])
logger = get_logger()


@router.post("/authorize", response_model=AuthorizationResponse)
async def authorize(request: AuthorizationRequest) -> AuthorizationResponse:
    """
    Check if a user is authorized to perform an action on a resource.

    This endpoint evaluates authorization using Casbin policies and returns
    a clear allow/deny decision with context.
    """
    casbin_service = get_casbin_service()
    # Perform authorization check
    allowed = casbin_service.authorize(
        user_id=request.user_id,
        action=request.action,
        resource=request.resource,
        domain=request.domain,
        resource_id=request.resource_id,
    )

    # Build response
    response = AuthorizationResponse(
        allowed=allowed,
        user_id=request.user_id,
        action=request.action,
        resource=request.resource,
        domain=request.domain,
        resource_id=request.resource_id,
        reason=None if allowed else "Access denied by policy",
    )

    logger.info(
        f"Authorization result: user={request.user_id}, "
        f"action={request.action}, resource={request.resource}, "
        f"domain={request.domain}, allowed={allowed}"
    )

    return response
