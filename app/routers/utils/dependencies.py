from uuid import UUID
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.role_service import RoleService
from app.models.role import Role


def get_role_by_id(
    role_id: UUID,
    db: Session = Depends(get_db),
) -> Role:
    """FastAPI dependency to get a role by ID.

    Args:
        role_id: The UUID of the role to retrieve
        db: Database session dependency

    Returns:
        Role: The retrieved role

    Raises:
        HTTPException: If the role is not found
    """
    role = RoleService(db).get_role(role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return role
