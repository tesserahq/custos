from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from uuid import UUID
from app.db import get_db
from app.services.permission_service import PermissionService
from app.schemas.permission import Permission, PermissionCreate, PermissionUpdate
from app.core.logging_config import get_logger
from app.commands.permission.create_permission_command import CreatePermissionCommand
from app.commands.permission.update_permission_command import UpdatePermissionCommand
from app.commands.permission.delete_permission_command import DeletePermissionCommand
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

router = APIRouter(prefix="/permissions", tags=["Permission"])
logger = get_logger()


@router.get("/", response_model=Page[Permission])
def list_permissions(db: Session = Depends(get_db)) -> Page[Permission]:
    """
    List all permissions with pagination.

    Returns a paginated response using fastapi-pagination.
    """
    permission_service = PermissionService(db)
    query = permission_service.get_permissions_query()
    return paginate(query)


@router.get("/{permission_id}", response_model=Permission)
def get_permission(permission_id: UUID, db: Session = Depends(get_db)) -> Permission:
    """
    Retrieve a specific permission by ID.

    Raises 404 if the permission is not found.
    """
    permission = PermissionService(db).get_permission(permission_id)
    if not permission:
        raise HTTPException(
            status_code=404, detail=f"Permission with id {permission_id} not found"
        )
    return permission


@router.get("/role/{role_id}", response_model=list[Permission])
def get_permissions_by_role(
    role_id: UUID, db: Session = Depends(get_db)
) -> list[Permission]:
    """
    Retrieve all permissions for a specific role.

    Raises 404 if the role is not found.
    """
    permission_service = PermissionService(db)
    permissions = permission_service.get_permissions_by_role(role_id)
    return permissions


@router.post("/", response_model=Permission, status_code=201)
def create_permission(
    permission_data: PermissionCreate, db: Session = Depends(get_db)
) -> Permission:
    """
    Create a new permission.

    Returns the created permission with a 201 status code.
    """
    try:
        command = CreatePermissionCommand(db)
        permission = command.execute(permission_data)
        logger.info(
            f"Created permission: {permission.id} ({permission.object}:{permission.action})"
        )
        return permission
    except ValueError as e:
        # Handle validation errors (e.g., duplicate object+action+role_id)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Failed to create permission: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create permission")


@router.put("/{permission_id}", response_model=Permission)
def update_permission(
    permission_id: UUID,
    permission_data: PermissionUpdate,
    db: Session = Depends(get_db),
) -> Permission:
    """
    Update an existing permission.

    Only provided fields will be updated. Raises 404 if the permission is not found.
    """
    try:
        command = UpdatePermissionCommand(db)
        updated_permission = command.execute(permission_id, permission_data)
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
def delete_permission(permission_id: UUID, db: Session = Depends(get_db)) -> None:
    """
    Delete a permission by ID.

    Returns 204 No Content on success. Raises 404 if the permission is not found.
    """
    try:
        command = DeletePermissionCommand(db)
        success = command.execute(permission_id)
        if not success:
            raise HTTPException(
                status_code=404, detail=f"Permission with id {permission_id} not found"
            )
        logger.info(f"Deleted permission: {permission_id}")
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
