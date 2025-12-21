from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from uuid import UUID
from app.db import get_db
from app.services.permission_service import PermissionService
from app.schemas.permission import Permission, PermissionUpdate
from app.core.logging_config import get_logger
from app.commands.permission.update_permission_command import UpdatePermissionCommand
from app.commands.permission.delete_permission_command import DeletePermissionCommand
from app.routers.utils.dependencies import get_permission_by_id

router = APIRouter(prefix="/permissions", tags=["Permission"])
logger = get_logger()


@router.get("/{permission_id}", response_model=Permission)
def get_permission(
    permission: Permission = Depends(get_permission_by_id),
) -> Permission:
    """
    Retrieve a specific permission by ID.

    Raises 404 if the permission is not found.
    """
    return permission


@router.put("/{permission_id}", response_model=Permission)
def update_permission(
    permission_data: PermissionUpdate,
    permission: Permission = Depends(get_permission_by_id),
    db: Session = Depends(get_db),
) -> Permission:
    """
    Update an existing permission.

    Only provided fields will be updated. Raises 404 if the permission is not found.
    """
    try:
        command = UpdatePermissionCommand(db)
        updated_permission = command.execute(permission.id, permission_data)
        logger.info(
            f"Updated permission: {updated_permission.id} ({updated_permission.object}:{updated_permission.action})"
        )
        return updated_permission
    except ValueError as e:
        # Handle validation errors (e.g., permission not found, duplicate object+action+role_id)
        error_message = str(e)
        if "not found" in error_message.lower():
            raise HTTPException(status_code=404, detail=error_message)
        else:
            raise HTTPException(status_code=400, detail=error_message)
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Failed to update permission: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update permission")


@router.delete("/{permission_id}", status_code=204)
def delete_permission(
    permission: Permission = Depends(get_permission_by_id),
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a permission by ID.

    Returns 204 No Content on success. Raises 404 if the permission is not found.
    """
    try:
        command = DeletePermissionCommand(db)
        success = command.execute(permission.id)
        if not success:
            raise HTTPException(
                status_code=404, detail=f"Permission with id {permission.id} not found"
            )
        logger.info(f"Deleted permission: {permission.id}")
    except ValueError as e:
        # Handle validation errors (e.g., permission not found)
        error_message = str(e)
        if "not found" in error_message.lower():
            raise HTTPException(status_code=404, detail=error_message)
        else:
            raise HTTPException(status_code=400, detail=error_message)
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Failed to delete permission: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete permission")
