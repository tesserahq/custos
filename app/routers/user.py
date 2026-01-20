from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.user_service import UserService
from app.services.membership_service import MembershipService
from app.services.casbin_service import get_casbin_service
from app.schemas.user import User, PermissionCheckRequest, PermissionCheckResponse
from app.schemas.membership import Membership
from uuid import UUID
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from app.routers.utils.dependencies import get_user_by_id
from app.core.logging_config import get_logger

router = APIRouter(prefix="/users", tags=["User"])
logger = get_logger()


@router.get("/", response_model=Page[User])
def list_users(
    q: str | None = Query(
        default=None, description="Search by first_name, last_name, or email"
    ),
    db: Session = Depends(get_db),
) -> Page[User]:
    """
    List all users with pagination.

    Returns a paginated response using fastapi-pagination.
    """
    user_service = UserService(db)
    query = user_service.get_users_query(q=q)
    return paginate(query)


@router.get("/{user_id}", response_model=User)
def get_user(user: User = Depends(get_user_by_id)) -> User:
    """
    Retrieve a specific user by ID.

    Raises 404 if the user is not found.
    """
    return user


@router.get("/{user_id}/memberships", response_model=Page[Membership])
def list_user_memberships(
    user: User = Depends(get_user_by_id), db: Session = Depends(get_db)
) -> Page[Membership]:
    """
    List all memberships for a specific user with pagination.

    Raises 404 if the user is not found.
    Returns a paginated response using fastapi-pagination.
    """
    membership_service = MembershipService(db)
    query = membership_service.get_memberships_by_user_query(user.id)
    return paginate(query)


@router.post("/{user_id}/permission-checks", response_model=PermissionCheckResponse)
def check_user_permission(
    request: PermissionCheckRequest,
    user: User = Depends(get_user_by_id),
) -> PermissionCheckResponse:
    """
    Check if a user has permission to perform an action on a resource.

    This endpoint evaluates authorization using Casbin policies and returns
    a clear allow/deny decision with context.

    Args:
        user: The user to check permissions for (from path parameter)
        request: Permission check request containing resource, action, and domain

    Returns:
        PermissionCheckResponse with the authorization decision

    Raises:
        404 if the user is not found
    """
    casbin_service = get_casbin_service()

    # Use domain from request or default to "*"
    domain = request.domain if request.domain is not None else "*"

    # Perform authorization check
    allowed = casbin_service.authorize(
        user_id=str(user.id),
        action=request.action,
        resource=request.resource,
        domain=domain,
    )

    # Build response
    response = PermissionCheckResponse(
        allowed=allowed,
        user_id=user.id,
        resource=request.resource,
        action=request.action,
        domain=domain,
        reason=None if allowed else "Access denied by policy",
    )

    logger.info(
        "Permission check result",
        extra={
            "user_id": str(user.id),
            "action": request.action,
            "resource": request.resource,
            "domain": domain,
            "allowed": allowed,
        },
    )

    return response
