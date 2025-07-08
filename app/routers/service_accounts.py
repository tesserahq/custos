from typing import List, Optional, Union
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.utils.auth import get_current_user
from app.models.user import User
from app.models.service_account import ServiceAccount
from app.services.service_account_service import ServiceAccountService
from app.services.casbin_service import casbin_service
from app.schemas.service_account import (
    ServiceAccountCreate,
    ServiceAccountUpdate,
    ServiceAccount as ServiceAccountSchema,
    ServiceAccountWithKey,
    ServiceAccountDetails,
)
from app.schemas.authorization import RoleAssignmentRequest, RoleAssignmentResponse
from app.core.logging_config import get_logger

router = APIRouter(prefix="/service-accounts", tags=["service-accounts"])
logger = get_logger()

# Union type for authenticated entities
AuthenticatedEntity = Union[User, ServiceAccount]


def get_entity_id(entity: AuthenticatedEntity) -> str:
    """Get the ID from either a User or ServiceAccount entity."""
    if isinstance(entity, ServiceAccount):
        return str(entity.id)
    elif isinstance(entity, User):
        return str(entity.id)
    else:
        raise ValueError("Invalid entity type")


def require_super_admin(
    entity: AuthenticatedEntity = Depends(get_current_user),
) -> AuthenticatedEntity:
    """Dependency to ensure the authenticated entity has super admin privileges."""
    if isinstance(entity, ServiceAccount):
        # For service accounts, check if they have admin roles
        service_account_roles = casbin_service.get_user_roles(str(entity.id))

        # Check for admin or super_admin role in any domain
        for domain in ["*", "global", "admin"]:  # Common admin domains
            domain_roles = casbin_service.get_user_roles(str(entity.id), domain)
            if "admin" in domain_roles or "super_admin" in domain_roles:
                return entity

        # Check if service account has admin role globally
        if "admin" in service_account_roles or "super_admin" in service_account_roles:
            return entity

        raise HTTPException(
            status_code=403, detail="Access denied. Super admin privileges required."
        )

    elif isinstance(entity, User):
        # For users, check if they have admin role in any domain or globally
        user_roles = casbin_service.get_user_roles(str(entity.id))

        # Check for admin or super_admin role in any domain
        for domain in ["*", "global", "admin"]:  # Common admin domains
            domain_roles = casbin_service.get_user_roles(str(entity.id), domain)
            if "admin" in domain_roles or "super_admin" in domain_roles:
                return entity

        # Check if user has admin role globally
        if "admin" in user_roles:
            return entity

        # Check if user has super_admin role globally
        if "super_admin" in user_roles:
            return entity

        raise HTTPException(
            status_code=403, detail="Access denied. Super admin privileges required."
        )

    else:
        raise HTTPException(status_code=401, detail="Invalid authentication type")


@router.post("/", response_model=ServiceAccountWithKey)
async def create_service_account(
    service_account: ServiceAccountCreate,
    current_user: AuthenticatedEntity = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> ServiceAccountWithKey:
    """
    Create a new service account.

    Only super admins can create service accounts.
    The API key is returned only during creation.
    """
    service = ServiceAccountService(db)

    try:
        created_account = service.create_service_account(
            service_account, created_by=UUID(get_entity_id(current_user))
        )

        logger.info(
            f"Service account created: id={created_account.id}, "
            f"name={created_account.name}, created_by={get_entity_id(current_user)}"
        )

        return created_account

    except Exception as e:
        logger.error(f"Failed to create service account: {e}")
        raise HTTPException(status_code=500, detail="Failed to create service account")


@router.get("/", response_model=List[ServiceAccountSchema])
async def list_service_accounts(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
    current_user: AuthenticatedEntity = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> List[ServiceAccountSchema]:
    """
    List all service accounts with pagination.

    Only super admins can view service accounts.
    """
    service = ServiceAccountService(db)
    service_accounts = service.get_service_accounts(skip=skip, limit=limit)

    logger.info(
        f"Service accounts listed: count={len(service_accounts)}, "
        f"requested_by={get_entity_id(current_user)}"
    )

    return service_accounts


@router.get("/active", response_model=List[ServiceAccountSchema])
async def list_active_service_accounts(
    current_user: AuthenticatedEntity = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> List[ServiceAccountSchema]:
    """
    List all active service accounts.

    Only super admins can view service accounts.
    """
    service = ServiceAccountService(db)
    service_accounts = service.get_active_service_accounts()

    logger.info(
        f"Active service accounts listed: count={len(service_accounts)}, "
        f"requested_by={get_entity_id(current_user)}"
    )

    return service_accounts


@router.get("/expired", response_model=List[ServiceAccountSchema])
async def list_expired_service_accounts(
    current_user: AuthenticatedEntity = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> List[ServiceAccountSchema]:
    """
    List all expired service accounts.

    Only super admins can view service accounts.
    """
    service = ServiceAccountService(db)
    service_accounts = service.get_expired_service_accounts()

    logger.info(
        f"Expired service accounts listed: count={len(service_accounts)}, "
        f"requested_by={get_entity_id(current_user)}"
    )

    return service_accounts


@router.get("/search")
async def search_service_accounts(
    name: Optional[str] = Query(
        None, description="Search by name (supports partial matches)"
    ),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    external_id: Optional[str] = Query(None, description="Search by external ID"),
    current_user: AuthenticatedEntity = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> List[ServiceAccountSchema]:
    """
    Search service accounts with various filters.

    Only super admins can search service accounts.
    """
    service = ServiceAccountService(db)

    # Build filters
    filters = {}
    if name:
        filters["name"] = {"operator": "ilike", "value": f"%{name}%"}
    if is_active is not None:
        filters["is_active"] = is_active
    if external_id:
        filters["external_id"] = external_id

    service_accounts = service.search(filters)

    logger.info(
        f"Service accounts searched: filters={filters}, "
        f"results_count={len(service_accounts)}, requested_by={get_entity_id(current_user)}"
    )

    return service_accounts


@router.get("/{service_account_id}", response_model=ServiceAccountSchema)
async def get_service_account(
    service_account_id: UUID,
    current_user: AuthenticatedEntity = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> ServiceAccountSchema:
    """
    Get a specific service account by ID.

    Only super admins can view service accounts.
    """
    service = ServiceAccountService(db)
    service_account = service.get_service_account(service_account_id)

    if not service_account:
        raise HTTPException(status_code=404, detail="Service account not found")

    logger.info(
        f"Service account retrieved: id={service_account_id}, "
        f"requested_by={get_entity_id(current_user)}"
    )

    return service_account


@router.put("/{service_account_id}", response_model=ServiceAccountSchema)
async def update_service_account(
    service_account_id: UUID,
    service_account_update: ServiceAccountUpdate,
    current_user: AuthenticatedEntity = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> ServiceAccountSchema:
    """
    Update a service account.

    Only super admins can update service accounts.
    """
    service = ServiceAccountService(db)

    # Check if service account exists
    existing_account = service.get_service_account(service_account_id)
    if not existing_account:
        raise HTTPException(status_code=404, detail="Service account not found")

    updated_account = service.update_service_account(
        service_account_id, service_account_update
    )

    if not updated_account:
        raise HTTPException(status_code=500, detail="Failed to update service account")

    logger.info(
        f"Service account updated: id={service_account_id}, "
        f"updated_by={get_entity_id(current_user)}"
    )

    return updated_account


@router.delete("/{service_account_id}")
async def delete_service_account(
    service_account_id: UUID,
    current_user: AuthenticatedEntity = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> dict:
    """
    Delete a service account.

    Only super admins can delete service accounts.
    """
    service = ServiceAccountService(db)

    # Check if service account exists
    existing_account = service.get_service_account(service_account_id)
    if not existing_account:
        raise HTTPException(status_code=404, detail="Service account not found")

    success = service.delete_service_account(service_account_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete service account")

    logger.info(
        f"Service account deleted: id={service_account_id}, "
        f"deleted_by={get_entity_id(current_user)}"
    )

    return {"message": "Service account deleted successfully"}


@router.post(
    "/{service_account_id}/regenerate-key", response_model=ServiceAccountWithKey
)
async def regenerate_api_key(
    service_account_id: UUID,
    current_user: AuthenticatedEntity = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> ServiceAccountWithKey:
    """
    Regenerate the API key for a service account.

    Only super admins can regenerate API keys.
    The new API key is returned only during regeneration.
    """
    service = ServiceAccountService(db)

    # Check if service account exists
    existing_account = service.get_service_account(service_account_id)
    if not existing_account:
        raise HTTPException(status_code=404, detail="Service account not found")

    updated_account = service.regenerate_api_key(service_account_id)

    if not updated_account:
        raise HTTPException(status_code=500, detail="Failed to regenerate API key")

    logger.info(
        f"API key regenerated: service_account_id={service_account_id}, "
        f"regenerated_by={get_entity_id(current_user)}"
    )

    return updated_account


@router.post("/{service_account_id}/activate")
async def activate_service_account(
    service_account_id: UUID,
    current_user: AuthenticatedEntity = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> ServiceAccountSchema:
    """
    Activate a service account.

    Only super admins can activate service accounts.
    """
    service = ServiceAccountService(db)

    # Check if service account exists
    existing_account = service.get_service_account(service_account_id)
    if not existing_account:
        raise HTTPException(status_code=404, detail="Service account not found")

    activated_account = service.activate_service_account(service_account_id)

    if not activated_account:
        raise HTTPException(
            status_code=500, detail="Failed to activate service account"
        )

    logger.info(
        f"Service account activated: id={service_account_id}, "
        f"activated_by={get_entity_id(current_user)}"
    )

    return activated_account


@router.post("/{service_account_id}/deactivate")
async def deactivate_service_account(
    service_account_id: UUID,
    current_user: AuthenticatedEntity = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> ServiceAccountSchema:
    """
    Deactivate a service account.

    Only super admins can deactivate service accounts.
    """
    service = ServiceAccountService(db)

    # Check if service account exists
    existing_account = service.get_service_account(service_account_id)
    if not existing_account:
        raise HTTPException(status_code=404, detail="Service account not found")

    deactivated_account = service.deactivate_service_account(service_account_id)

    if not deactivated_account:
        raise HTTPException(
            status_code=500, detail="Failed to deactivate service account"
        )

    logger.info(
        f"Service account deactivated: id={service_account_id}, "
        f"deactivated_by={get_entity_id(current_user)}"
    )

    return deactivated_account


@router.post("/{service_account_id}/assign-role", response_model=RoleAssignmentResponse)
async def assign_role_to_service_account(
    service_account_id: UUID,
    request: RoleAssignmentRequest,
    current_user: AuthenticatedEntity = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> RoleAssignmentResponse:
    """
    Assign a role to a service account.

    Only super admins can assign roles to service accounts.
    """
    service = ServiceAccountService(db)

    # Check if service account exists
    existing_account = service.get_service_account(service_account_id)
    if not existing_account:
        raise HTTPException(status_code=404, detail="Service account not found")

    # Assign role using the service account's Casbin integration
    success = service.assign_role(
        service_account_id=service_account_id, role=request.role, domain=request.domain
    )

    if not success:
        raise HTTPException(
            status_code=400, detail="Failed to assign role to service account"
        )

    response = RoleAssignmentResponse(
        success=True,
        user_id=str(service_account_id),
        role=request.role,
        domain=request.domain,
        resource=request.resource,
        message=f"Role '{request.role}' successfully assigned to service account '{service_account_id}'",
    )

    logger.info(
        f"Role assigned to service account: service_account_id={service_account_id}, "
        f"role={request.role}, domain={request.domain}, assigned_by={get_entity_id(current_user)}"
    )

    return response


@router.delete(
    "/{service_account_id}/remove-role", response_model=RoleAssignmentResponse
)
async def remove_role_from_service_account(
    service_account_id: UUID,
    request: RoleAssignmentRequest,
    current_user: AuthenticatedEntity = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> RoleAssignmentResponse:
    """
    Remove a role from a service account.

    Only super admins can remove roles from service accounts.
    """
    service = ServiceAccountService(db)

    # Check if service account exists
    existing_account = service.get_service_account(service_account_id)
    if not existing_account:
        raise HTTPException(status_code=404, detail="Service account not found")

    # Remove role using the service account's Casbin integration
    success = service.remove_role(
        service_account_id=service_account_id, role=request.role, domain=request.domain
    )

    if not success:
        raise HTTPException(
            status_code=400, detail="Failed to remove role from service account"
        )

    response = RoleAssignmentResponse(
        success=True,
        user_id=str(service_account_id),
        role=request.role,
        domain=request.domain,
        resource=request.resource,
        message=f"Role '{request.role}' successfully removed from service account '{service_account_id}'",
    )

    logger.info(
        f"Role removed from service account: service_account_id={service_account_id}, "
        f"role={request.role}, domain={request.domain}, removed_by={get_entity_id(current_user)}"
    )

    return response


@router.get("/{service_account_id}/roles")
async def get_service_account_roles(
    service_account_id: UUID,
    domain: Optional[str] = Query(None, description="Domain to filter roles by"),
    current_user: AuthenticatedEntity = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> dict:
    """
    Get all roles assigned to a service account.

    Only super admins can view service account roles.
    """
    service = ServiceAccountService(db)

    # Check if service account exists
    existing_account = service.get_service_account(service_account_id)
    if not existing_account:
        raise HTTPException(status_code=404, detail="Service account not found")

    roles = service.get_roles(service_account_id, domain)

    logger.info(
        f"Service account roles retrieved: service_account_id={service_account_id}, "
        f"domain={domain}, roles_count={len(roles)}, requested_by={get_entity_id(current_user)}"
    )

    return {
        "service_account_id": str(service_account_id),
        "domain": domain,
        "roles": roles,
        "roles_count": len(roles),
    }


@router.get("/{service_account_id}/permissions")
async def get_service_account_permissions(
    service_account_id: UUID,
    domain: Optional[str] = Query(None, description="Domain to filter permissions by"),
    current_user: AuthenticatedEntity = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> dict:
    """
    Get all permissions for a service account.

    Only super admins can view service account permissions.
    """
    service = ServiceAccountService(db)

    # Check if service account exists
    existing_account = service.get_service_account(service_account_id)
    if not existing_account:
        raise HTTPException(status_code=404, detail="Service account not found")

    permissions = service.get_permissions(service_account_id, domain)

    # Convert permission tuples to readable format
    formatted_permissions = []
    for perm_tuple in permissions:
        if len(perm_tuple) >= 4:
            # Format: "resource:action" for domain-based model
            if perm_tuple[2] and perm_tuple[3]:  # object and action
                formatted_permissions.append(f"{perm_tuple[2]}:{perm_tuple[3]}")
        elif len(perm_tuple) >= 3:
            # Format: "resource:action" for non-domain model
            if perm_tuple[1] and perm_tuple[2]:  # object and action
                formatted_permissions.append(f"{perm_tuple[1]}:{perm_tuple[2]}")

    logger.info(
        f"Service account permissions retrieved: service_account_id={service_account_id}, "
        f"domain={domain}, permissions_count={len(formatted_permissions)}, "
        f"requested_by={get_entity_id(current_user)}"
    )

    return {
        "service_account_id": str(service_account_id),
        "domain": domain,
        "permissions": formatted_permissions,
        "permissions_count": len(formatted_permissions),
    }


@router.post("/{service_account_id}/authorize")
async def check_service_account_authorization(
    service_account_id: UUID,
    action: str,
    resource: str,
    domain: Optional[str] = None,
    resource_id: Optional[str] = None,
    current_user: AuthenticatedEntity = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> dict:
    """
    Check if a service account is authorized to perform an action.

    Only super admins can check service account authorization.
    """
    service = ServiceAccountService(db)

    # Check if service account exists
    existing_account = service.get_service_account(service_account_id)
    if not existing_account:
        raise HTTPException(status_code=404, detail="Service account not found")

    authorized = service.authorize(
        service_account_id=service_account_id,
        action=action,
        resource=resource,
        domain=domain,
        resource_id=resource_id,
    )

    logger.info(
        f"Service account authorization checked: service_account_id={service_account_id}, "
        f"action={action}, resource={resource}, domain={domain}, "
        f"resource_id={resource_id}, authorized={authorized}, "
        f"checked_by={get_entity_id(current_user)}"
    )

    return {
        "service_account_id": str(service_account_id),
        "action": action,
        "resource": resource,
        "domain": domain,
        "resource_id": resource_id,
        "authorized": authorized,
        "reason": "Access granted" if authorized else "Access denied by policy",
    }
