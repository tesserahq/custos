from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from app.schemas.authorization import (
    AuthorizationRequest,
    AuthorizationResponse,
    RoleAssignmentRequest,
    RoleAssignmentResponse,
    PermissionRequest,
    PermissionResponse,
    RoleDefinitionRequest,
    RoleDefinitionResponse,
    RoleListResponse,
)
from app.services.casbin_service import casbin_service
from app.services.role_definition_service import role_definition_service
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


@router.post("/assign-role", response_model=RoleAssignmentResponse)
async def assign_role(request: RoleAssignmentRequest) -> RoleAssignmentResponse:
    """
    Assign a role to a user.

    This endpoint assigns a role to a user, optionally scoped to a specific
    domain for multi-tenancy support.
    """
    # Assign role
    success = casbin_service.assign_role(
        user_id=request.user_id,
        role=request.role,
        domain=request.domain,
        resource=request.resource,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to assign role. Role may already exist or be invalid.",
        )

    response = RoleAssignmentResponse(
        success=True,
        user_id=request.user_id,
        role=request.role,
        domain=request.domain,
        resource=request.resource,
        message=f"Role '{request.role}' successfully assigned to user '{request.user_id}'",
    )

    logger.info(
        f"Role assigned: user={request.user_id}, role={request.role}, "
        f"domain={request.domain}, resource={request.resource}"
    )

    return response


@router.delete("/remove-role", response_model=RoleAssignmentResponse)
async def remove_role(request: RoleAssignmentRequest) -> RoleAssignmentResponse:
    """
    Remove a role from a user.

    This endpoint removes a role from a user, optionally scoped to a specific
    domain for multi-tenancy support.
    """

    # Remove role
    success = casbin_service.remove_role(
        user_id=request.user_id, role=request.role, domain=request.domain
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to remove role. Role may not exist or be invalid.",
        )

    response = RoleAssignmentResponse(
        success=True,
        user_id=request.user_id,
        role=request.role,
        domain=request.domain,
        resource=request.resource,
        message=f"Role '{request.role}' successfully removed from user '{request.user_id}'",
    )

    logger.info(
        f"Role removed: user={request.user_id}, role={request.role}, "
        f"domain={request.domain}"
    )

    return response


@router.post("/permissions", response_model=PermissionResponse)
async def get_permissions(request: PermissionRequest) -> PermissionResponse:
    """
    Get all permissions for a user.

    This endpoint returns all permissions and roles assigned to a user,
    optionally filtered by domain and resource.
    """
    # Get user roles
    roles = casbin_service.get_user_roles(
        user_id=request.user_id, domain=request.domain
    )

    # Get user permissions
    permissions_tuples = casbin_service.get_user_permissions(
        user_id=request.user_id, domain=request.domain, resource=request.resource
    )

    # Convert permission tuples to strings
    permissions = []
    for perm_tuple in permissions_tuples:
        if len(perm_tuple) >= 4:
            # Format: "resource:action" for domain-based model (subject, domain, object, action)
            if perm_tuple[2] and perm_tuple[3]:  # object and action
                permissions.append(f"{perm_tuple[2]}:{perm_tuple[3]}")
        elif len(perm_tuple) >= 3:
            # Format: "resource:action" for non-domain model (subject, object, action)
            if perm_tuple[1] and perm_tuple[2]:  # object and action
                permissions.append(f"{perm_tuple[1]}:{perm_tuple[2]}")

    response = PermissionResponse(
        user_id=request.user_id,
        domain=request.domain,
        permissions=permissions,
        roles=roles,
    )

    logger.info(
        f"Permissions retrieved: user={request.user_id}, "
        f"domain={request.domain}, roles_count={len(roles)}, "
        f"permissions_count={len(permissions)}"
    )

    return response


@router.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint for the authorization service.

    Returns basic service status information.
    """
    try:
        # Basic health check - try to access the enforcer
        if casbin_service.enforcer is not None:
            return {
                "status": "healthy",
                "service": "custos-authorization",
                "casbin_enforcer": "initialized",
            }
        else:
            return {
                "status": "unhealthy",
                "service": "custos-authorization",
                "casbin_enforcer": "not_initialized",
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "custos-authorization",
            "error": str(e),
        }


@router.post("/define-role", response_model=RoleDefinitionResponse)
async def define_role(request: RoleDefinitionRequest) -> RoleDefinitionResponse:
    """
    Define a role with specific permissions.

    This endpoint creates a role and assigns permissions to it.
    """
    try:
        if request.role_type == "admin":
            success = role_definition_service.define_admin_role(request.domain)
        elif request.role_type == "editor":
            success = role_definition_service.define_editor_role(request.domain)
        elif request.role_type == "viewer":
            success = role_definition_service.define_viewer_role(request.domain)
        elif request.role_type == "custom":
            if not request.custom_permissions:
                raise HTTPException(
                    status_code=400,
                    detail="Custom permissions are required for custom role type",
                )
            success = role_definition_service.define_custom_role(
                request.role_name, request.domain, request.custom_permissions
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role type: {request.role_type}. Must be one of: admin, editor, viewer, custom",
            )

        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to define role. Check logs for details."
            )

        response = RoleDefinitionResponse(
            success=True,
            role_name=request.role_name or request.role_type,
            domain=request.domain,
            role_type=request.role_type,
            message=f"Role '{request.role_name or request.role_type}' successfully defined in domain '{request.domain}'",
        )

        logger.info(
            f"Role defined: name={request.role_name or request.role_type}, "
            f"type={request.role_type}, domain={request.domain}"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to define role: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error while defining role"
        )


@router.get("/roles/{domain}", response_model=RoleListResponse)
async def list_roles(domain: str) -> RoleListResponse:
    """
    List all roles defined for a domain.

    This endpoint returns all roles that have been defined for the specified domain.
    """
    try:
        roles = role_definition_service.list_defined_roles(domain)

        response = RoleListResponse(domain=domain, roles=roles, count=len(roles))

        logger.info(f"Roles listed for domain {domain}: {len(roles)} roles found")

        return response

    except Exception as e:
        logger.error(f"Failed to list roles for domain {domain}: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error while listing roles"
        )


@router.get("/roles/{domain}/{role_name}/permissions")
async def get_role_permissions(domain: str, role_name: str) -> dict:
    """
    Get all permissions for a specific role in a domain.

    This endpoint returns all permissions assigned to the specified role.
    """
    try:
        permissions = role_definition_service.get_role_permissions(role_name, domain)

        # Convert to a more readable format
        formatted_permissions = [
            f"{resource}:{action}" for resource, action in permissions
        ]

        response = {
            "role_name": role_name,
            "domain": domain,
            "permissions": formatted_permissions,
            "count": len(permissions),
        }

        logger.info(
            f"Permissions retrieved for role '{role_name}' in domain {domain}: {len(permissions)} permissions"
        )

        return response

    except Exception as e:
        logger.error(
            f"Failed to get permissions for role '{role_name}' in domain {domain}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error while getting role permissions",
        )


@router.post("/setup-default-roles/{domain}")
async def setup_default_roles(domain: str) -> dict:
    """
    Set up all default roles (admin, editor, viewer) for a domain.

    This endpoint creates the standard role hierarchy for a new domain.
    """
    try:
        results = role_definition_service.setup_default_roles(domain)

        success_count = sum(1 for success in results.values() if success)
        total_roles = len(results)

        response = {
            "domain": domain,
            "results": results,
            "success_count": success_count,
            "total_roles": total_roles,
            "message": f"Default roles setup completed: {success_count}/{total_roles} roles created successfully",
        }

        logger.info(
            f"Default roles setup for domain {domain}: {success_count}/{total_roles} successful"
        )

        return response

    except Exception as e:
        logger.error(f"Failed to setup default roles for domain {domain}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while setting up default roles",
        )
