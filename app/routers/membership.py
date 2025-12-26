from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from uuid import UUID
from app.db import get_db
from app.services.membership_service import MembershipService
from app.services.role_service import RoleService
from app.schemas.membership import Membership
from app.core.logging_config import get_logger
from app.commands.binding.delete_binding_command import DeleteBindingCommand
from app.routers.utils.dependencies import get_membership_by_id
from app.models.role import Role as RoleModel

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
    membership: Membership = Depends(get_membership_by_id),
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a membership by ID.

    This will also remove the role binding from Casbin.
    Returns 204 No Content on success. Raises 404 if the membership is not found.
    """
    try:
        # Get the role to pass to DeleteBindingCommand
        role_service = RoleService(db)
        role = role_service.get_role(membership.role_id)
        if not role:
            raise HTTPException(
                status_code=404, detail=f"Role with id {membership.role_id} not found"
            )

        # Use DeleteBindingCommand to remove from both Casbin and database
        command = DeleteBindingCommand(db)
        response = command.execute(
            role=role,
            user_id=str(membership.user_id),
            domain=None,  # Memberships don't store domain, so we remove globally
            resource=None,
        )

        if not response.success:
            raise HTTPException(
                status_code=400,
                detail="Failed to remove role binding from Casbin",
            )

        logger.info(f"Deleted membership: {membership.id}")
    except ValueError as e:
        # Handle validation errors (e.g., role not found, binding removal failed)
        error_message = str(e)
        if "not found" in error_message.lower():
            raise HTTPException(status_code=404, detail=error_message)
        else:
            raise HTTPException(status_code=400, detail=error_message)
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Failed to delete membership: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete membership")
