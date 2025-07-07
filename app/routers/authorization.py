from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from app.schemas.authorization import (
    AuthorizationRequest,
    AuthorizationResponse,
    RoleAssignmentRequest,
    RoleAssignmentResponse,
    PermissionRequest,
    PermissionResponse,
)
from app.services.casbin_service import casbin_service
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
    try:
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

    except Exception as e:
        logger.error(f"Authorization check failed: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error during authorization check"
        )


@router.post("/assign-role", response_model=RoleAssignmentResponse)
async def assign_role(request: RoleAssignmentRequest) -> RoleAssignmentResponse:
    """
    Assign a role to a user.

    This endpoint assigns a role to a user, optionally scoped to a specific
    domain for multi-tenancy support.
    """
    try:
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Role assignment failed: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error during role assignment"
        )


@router.delete("/remove-role", response_model=RoleAssignmentResponse)
async def remove_role(request: RoleAssignmentRequest) -> RoleAssignmentResponse:
    """
    Remove a role from a user.

    This endpoint removes a role from a user, optionally scoped to a specific
    domain for multi-tenancy support.
    """
    try:
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Role removal failed: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error during role removal"
        )


@router.post("/permissions", response_model=PermissionResponse)
async def get_permissions(request: PermissionRequest) -> PermissionResponse:
    """
    Get all permissions for a user.

    This endpoint returns all permissions and roles assigned to a user,
    optionally filtered by domain and resource.
    """
    try:
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

    except Exception as e:
        logger.error(f"Failed to get permissions: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error while retrieving permissions"
        )


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
