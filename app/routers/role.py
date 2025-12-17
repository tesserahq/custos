from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from uuid import UUID
from app.db import get_db
from app.services.role_service import RoleService
from app.services.permission_service import PermissionService
from app.schemas.role import Role, RoleCreate, RoleUpdate
from app.schemas.permission import Permission, PermissionCreateRequest
from app.core.logging_config import get_logger
from app.commands.role.create_role_command import CreateRoleCommand
from app.commands.role.update_role_command import UpdateRoleCommand
from app.commands.role.delete_role_command import DeleteRoleCommand
from app.commands.permission.create_permission_command import CreatePermissionCommand
from app.schemas.permission import PermissionCreate
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

router = APIRouter(prefix="/roles", tags=["Role"])
logger = get_logger()


@router.get("/", response_model=Page[Role])
def list_roles(db: Session = Depends(get_db)) -> Page[Role]:
    """
    List all roles with pagination.

    Returns a paginated response using fastapi-pagination.
    """
    role_service = RoleService(db)
    query = role_service.get_roles_query()
    return paginate(query)


@router.get("/{role_id}", response_model=Role)
def get_role(role_id: UUID, db: Session = Depends(get_db)) -> Role:
    """
    Retrieve a specific role by ID.

    Raises 404 if the role is not found.
    """
    role = RoleService(db).get_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail=f"Role with id {role_id} not found")
    return role


@router.post("/", response_model=Role, status_code=201)
def create_role(role_data: RoleCreate, db: Session = Depends(get_db)) -> Role:
    """
    Create a new role.

    Returns the created role with a 201 status code.
    """
    try:
        command = CreateRoleCommand(db)
        role = command.execute(role_data)
        logger.info(f"Created role: {role.id} ({role.name})")
        return role
    except ValueError as e:
        # Handle validation errors (e.g., duplicate name)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Failed to create role: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create role")


@router.put("/{role_id}", response_model=Role)
def update_role(
    role_id: UUID, role_data: RoleUpdate, db: Session = Depends(get_db)
) -> Role:
    """
    Update an existing role.

    Only provided fields will be updated. Raises 404 if the role is not found.
    """
    try:
        command = UpdateRoleCommand(db)
        updated_role = command.execute(role_id, role_data)
        logger.info(f"Updated role: {updated_role.id} ({updated_role.name})")
        return updated_role
    except ValueError as e:
        # Handle validation errors (e.g., role not found, duplicate name)
        error_message = str(e)
        if "not found" in error_message.lower():
            raise HTTPException(status_code=404, detail=error_message)
        else:
            raise HTTPException(status_code=400, detail=error_message)
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Failed to update role: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update role")


@router.delete("/{role_id}", status_code=204)
def delete_role(role_id: UUID, db: Session = Depends(get_db)) -> None:
    """
    Delete a role by ID.

    Returns 204 No Content on success. Raises 404 if the role is not found.
    """
    try:
        command = DeleteRoleCommand(db)
        success = command.execute(role_id)
        if not success:
            raise HTTPException(
                status_code=404, detail=f"Role with id {role_id} not found"
            )
        logger.info(f"Deleted role: {role_id}")
    except ValueError as e:
        # Handle validation errors (e.g., role not found)
        error_message = str(e)
        if "not found" in error_message.lower():
            raise HTTPException(status_code=404, detail=error_message)
        else:
            raise HTTPException(status_code=400, detail=error_message)
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Failed to delete role: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete role")


@router.get("/{role_id}/permissions", response_model=list[Permission])
def list_role_permissions(role_id: UUID, db: Session = Depends(get_db)):
    """
    List all permissions for a specific role.

    Raises 404 if the role is not found.
    """
    # Validate role exists
    role = RoleService(db).get_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail=f"Role with id {role_id} not found")

    permission_service = PermissionService(db)
    permissions = permission_service.get_permissions_by_role(role_id)
    return permissions


@router.post("/{role_id}/permissions", response_model=Permission, status_code=201)
def create_role_permission(
    role_id: UUID,
    permission_data: PermissionCreateRequest,
    db: Session = Depends(get_db),
) -> Permission:
    """
    Create a new permission for a specific role.

    The role_id is taken from the URL path, not the request body.
    Returns the created permission with a 201 status code.
    """
    # Validate role exists
    role = RoleService(db).get_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail=f"Role with id {role_id} not found")

    try:
        # Create PermissionCreate with role_id from URL
        permission_create = PermissionCreate(
            object=permission_data.object,
            action=permission_data.action,
            role_id=role_id,
        )
        command = CreatePermissionCommand(db)
        permission = command.execute(permission_create)
        logger.info(
            f"Created permission: {permission.id} ({permission.object}:{permission.action}) for role {role_id}"
        )
        return permission
    except ValueError as e:
        # Handle validation errors (e.g., duplicate object+action+role_id)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Failed to create permission: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create permission")
