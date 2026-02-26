from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.role_service import RoleService
from app.schemas.membership import Membership
from app.core.logging_config import get_logger
from app.commands.memberships.delete_membership_command import DeleteMembershipCommand
from app.routers.utils.dependencies import get_membership_by_id
from app.models.user import User

router = APIRouter(prefix="/memberships", tags=["Membership"])
logger = get_logger()


@router.get("/{membership_id}", response_model=Membership)
def get_membership(
    membership: Membership = Depends(get_membership_by_id),
) -> Membership:
    """
    Retrieve a specific membership by ID.

    Raises 404 if the membership is not found.
    """
    return membership


@router.delete("/{membership_id}", status_code=204)
def delete_membership(
    request: Request,
    membership: Membership = Depends(get_membership_by_id),
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a membership by ID.

    This will also remove the role binding from Casbin.
    Users cannot delete their own membership - someone else must remove them from a role.

    Returns 204 No Content on success. Raises 403 if attempting to delete own membership.
    Raises 404 if the membership is not found.
    """
    # Get the current user from request state (set by authentication middleware)
    deleted_by: User = request.state.user

    # Get the role to pass to DeleteBindingCommand
    role_service = RoleService(db)
    role = role_service.get_role(membership.role_id)
    if not role:
        raise HTTPException(
            status_code=404, detail=f"Role with id {membership.role_id} not found"
        )

    # Use DeleteMembershipCommand to remove from both Casbin and database
    command = DeleteMembershipCommand(db)
    response = command.execute(
        role=role,
        user_id=membership.user_id,
        domain=None,  # Memberships don't store domain, so we remove globally
        resource=None,
        deleted_by=deleted_by,
    )

    if not response.success:
        raise HTTPException(
            status_code=400,
            detail="Failed to remove role binding from Casbin",
        )
