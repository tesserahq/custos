from uuid import UUID
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.role_service import RoleService
from app.services.permission_service import PermissionService
from app.services.membership_service import MembershipService
from app.models.role import Role
from app.models.permission import Permission
from app.schemas.membership import Membership


def get_role_by_id(
    role_id: str,
    db: Session = Depends(get_db),
) -> Role:
    """FastAPI dependency to get a role by ID or identifier.

    This function accepts either a UUID or a role identifier string.
    It first attempts to parse the input as a UUID. If successful,
    it searches by role ID. If not, it searches by identifier.

    Args:
        role_id: The UUID or identifier string of the role to retrieve
        db: Database session dependency

    Returns:
        Role: The retrieved role

    Raises:
        HTTPException: If the role is not found
    """
    role_service = RoleService(db)

    # Try to parse as UUID first
    try:
        role_uuid = UUID(role_id)
        role = role_service.get_role(role_uuid)
    except ValueError:
        # Not a valid UUID, treat as identifier
        role = role_service.get_role_by_identifier(role_id)

    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


def get_permission_by_id(
    permission_id: UUID,
    db: Session = Depends(get_db),
) -> Permission:
    """FastAPI dependency to get a permission by ID.

    Args:
        permission_id: The UUID of the permission to retrieve
        db: Database session dependency

    Returns:
        Permission: The retrieved permission

    Raises:
        HTTPException: If the permission is not found
    """
    permission = PermissionService(db).get_permission(permission_id)
    if permission is None:
        raise HTTPException(status_code=404, detail="Permission not found")
    return permission


def get_membership_by_id(
    membership_id: UUID,
    db: Session = Depends(get_db),
) -> Membership:
    """FastAPI dependency to get a membership by ID.

    Args:
        membership_id: The UUID of the membership to retrieve
        db: Database session dependency

    Returns:
        Membership: The retrieved membership

    Raises:
        HTTPException: If the membership is not found
    """
    membership = MembershipService(db).get_membership(membership_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")
    return Membership.model_validate(membership)
