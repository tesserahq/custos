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
    RoleConfigRequest,
    RoleConfigResponse,
    RoleConfigValidationRequest,
    RoleConfigValidationResponse,
    SetupRolesRequest,
)
from app.services.casbin_service import casbin_service
from app.services.role_definition_service import role_definition_service
from app.services.role_config_service import role_config_service
from app.services.role_template_service import role_template_service
from app.core.logging_config import get_logger
import json

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


@router.post("/setup-roles", response_model=RoleConfigResponse)
async def setup_roles(request: SetupRolesRequest) -> RoleConfigResponse:
    """
    Set up roles for a domain using YAML, CSV, or JSON content.
    The request body must specify the type and provide the content.
    """
    try:
        if request.type == "yaml":
            validation = role_config_service.validate_yaml_content(request.content)
            if not validation["valid"]:
                return RoleConfigResponse(
                    success=False,
                    domain=request.domain,
                    config_name=None,
                    results={},
                    success_count=0,
                    total_roles=0,
                    message=f"Invalid YAML configuration: {validation.get('error', 'Unknown error')}",
                    validation_errors=validation.get(
                        "errors", [validation.get("error", "Unknown error")]
                    ),
                )
            results = role_config_service.define_roles_from_yaml_content(
                request.domain, request.content
            )
        elif request.type == "json":
            # Accept both dict and string for content
            json_config = request.content
            if isinstance(json_config, str):
                try:
                    json_config = json.loads(json_config)
                except Exception as e:
                    return RoleConfigResponse(
                        success=False,
                        domain=request.domain,
                        config_name=None,
                        results={},
                        success_count=0,
                        total_roles=0,
                        message=f"Invalid JSON: {e}",
                        validation_errors=[str(e)],
                    )
            validation = role_config_service.validate_json_content(json_config)
            if not validation["valid"]:
                return RoleConfigResponse(
                    success=False,
                    domain=request.domain,
                    config_name=None,
                    results={},
                    success_count=0,
                    total_roles=0,
                    message=f"Invalid JSON configuration: {validation.get('error', 'Unknown error')}",
                    validation_errors=validation.get(
                        "errors", [validation.get("error", "Unknown error")]
                    ),
                )
            results = role_config_service.define_roles_from_json_content(
                request.domain, json_config
            )
        elif request.type == "csv":
            import io
            import csv

            csv_reader = csv.reader(io.StringIO(request.content))
            policies = [row for row in csv_reader if row and not row[0].startswith("#")]
            role_policies = {}
            for policy in policies:
                if len(policy) >= 5:
                    role = policy[1].strip()
                    resource = policy[3].strip()
                    action = policy[4].strip()
                    if role not in role_policies:
                        role_policies[role] = []
                    role_policies[role].append((resource, action))
            results = {}
            for role_name, permissions in role_policies.items():
                success = role_config_service._define_role_permissions(
                    role_name, request.domain, permissions
                )
                results[role_name] = success
        else:
            return RoleConfigResponse(
                success=False,
                domain=request.domain,
                config_name=None,
                results={},
                success_count=0,
                total_roles=0,
                message="Invalid type. Must be one of: yaml, csv, json",
                validation_errors=["Invalid type. Must be one of: yaml, csv, json"],
            )

        success_count = sum(1 for success in results.values() if success)
        total_roles = len(results)

        response = RoleConfigResponse(
            success=success_count > 0,
            domain=request.domain,
            config_name=None,
            results=results,
            success_count=success_count,
            total_roles=total_roles,
            message=f"Roles setup completed: {success_count}/{total_roles} roles created successfully",
            validation_errors=None,
        )
        logger.info(
            f"Roles setup for domain {request.domain}: {success_count}/{total_roles} successful"
        )
        return response

    except Exception as e:
        logger.error(f"Failed to setup roles for domain {request.domain}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while setting up roles",
        )


@router.get("/available-roles")
async def get_available_roles(config_file: str = "roles.yaml") -> dict:
    """
    Get list of available roles from configuration files.

    This endpoint returns all roles defined in the configuration files.
    """
    try:
        roles = role_config_service.get_available_roles(config_file)

        response = {
            "config_file": config_file,
            "available_roles": roles,
            "count": len(roles),
        }

        logger.info(f"Available roles from {config_file}: {len(roles)} roles found")

        return response

    except Exception as e:
        logger.error(f"Failed to get available roles from {config_file}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while getting available roles",
        )


@router.get("/validate-config")
async def validate_configuration(config_file: str = "roles.yaml") -> dict:
    """
    Validate role configuration files.

    This endpoint validates the structure and content of role configuration files.
    """
    try:
        validation_result = role_config_service.validate_configuration(config_file)

        response = {
            "config_file": config_file,
            "valid": validation_result["valid"],
            "errors": validation_result.get("errors", []),
            "warnings": validation_result.get("warnings", []),
        }

        logger.info(
            f"Configuration validation for {config_file}: valid={validation_result['valid']}"
        )

        return response

    except Exception as e:
        logger.error(f"Failed to validate configuration {config_file}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while validating configuration",
        )


@router.post("/validate-yaml-content", response_model=RoleConfigValidationResponse)
async def validate_yaml_content(
    request: RoleConfigValidationRequest,
) -> RoleConfigValidationResponse:
    """
    Validate YAML content for role configuration.

    This endpoint validates YAML content without creating any roles.
    """
    try:
        validation = role_config_service.validate_yaml_content(request.yaml_content)

        response = RoleConfigValidationResponse(
            valid=validation["valid"],
            config_name=request.config_name,
            errors=validation.get("errors", []),
            warnings=validation.get("warnings", []),
            available_roles=validation.get("available_roles", []),
            total_permissions=validation.get("total_permissions", 0),
        )

        logger.info(f"YAML content validation: valid={validation['valid']}")

        return response

    except Exception as e:
        logger.error(f"Failed to validate YAML content: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while validating YAML content",
        )


@router.post("/validate-json-content", response_model=RoleConfigValidationResponse)
async def validate_json_content(
    request: RoleConfigValidationRequest,
) -> RoleConfigValidationResponse:
    """
    Validate JSON content for role configuration.

    This endpoint validates JSON content without creating any roles.
    """
    try:
        validation = role_config_service.validate_json_content(request.content)

        response = RoleConfigValidationResponse(
            valid=validation["valid"],
            config_name=request.config_name,
            errors=validation.get("errors", []),
            warnings=validation.get("warnings", []),
            available_roles=validation.get("available_roles", []),
            total_permissions=validation.get("total_permissions", 0),
        )

        logger.info(f"JSON content validation: valid={validation['valid']}")

        return response

    except Exception as e:
        logger.error(f"Failed to validate JSON content: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while validating JSON content",
        )


@router.post("/templates", response_model=dict)
async def create_role_template(request: dict) -> dict:
    """
    Create a new role template.

    Request body:
    {
        "template_name": "standard-roles",
        "role_config": {
            "roles": {
                "admin": {
                    "permissions": {
                        "users": ["read", "write", "delete", "create"],
                        "documents": ["read", "write", "delete", "create"]
                    }
                }
            }
        }
    }
    """
    try:
        template_name = request.get("template_name")
        role_config = request.get("role_config")

        if not template_name or not role_config:
            raise HTTPException(
                status_code=400, detail="template_name and role_config are required"
            )

        success = role_template_service.create_role_template(template_name, role_config)

        if success:
            return {
                "success": True,
                "template_name": template_name,
                "message": f"Template '{template_name}' created successfully",
            }
        else:
            raise HTTPException(
                status_code=500, detail=f"Failed to create template '{template_name}'"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create role template: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error while creating template"
        )


@router.get("/templates", response_model=dict)
async def list_role_templates() -> dict:
    """
    List all available role templates.
    """
    try:
        templates = role_template_service.list_role_templates()

        return {"templates": templates, "count": len(templates)}

    except Exception as e:
        logger.error(f"Failed to list role templates: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error while listing templates"
        )


@router.get("/templates/{template_name}", response_model=dict)
async def get_role_template(template_name: str) -> dict:
    """
    Get a specific role template.
    """
    try:
        config = role_template_service.get_role_template(template_name)

        if not config:
            raise HTTPException(
                status_code=404, detail=f"Template '{template_name}' not found"
            )

        return {"template_name": template_name, "config": config}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get role template {template_name}: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error while getting template"
        )


@router.post("/templates/{template_name}/apply", response_model=dict)
async def apply_template_to_domain(template_name: str, request: dict) -> dict:
    """
    Apply a role template to a domain.

    Request body:
    {
        "domain": "tenant-123",
        "overwrite_existing": false
    }
    """
    try:
        domain = request.get("domain")
        overwrite_existing = request.get("overwrite_existing", False)

        if not domain:
            raise HTTPException(status_code=400, detail="domain is required")

        results = role_template_service.apply_template_to_domain(
            template_name, domain, overwrite_existing
        )

        return {
            "template_name": template_name,
            "domain": domain,
            "results": results,
            "success": "error" not in results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to apply template {template_name} to domain {domain}: {e}"
        )
        raise HTTPException(
            status_code=500, detail="Internal server error while applying template"
        )


@router.post("/templates/{template_name}/apply-multiple", response_model=dict)
async def apply_template_to_multiple_domains(template_name: str, request: dict) -> dict:
    """
    Apply a role template to multiple domains.

    Request body:
    {
        "domains": ["tenant-1", "tenant-2", "tenant-3"],
        "overwrite_existing": false
    }
    """
    try:
        domains = request.get("domains", [])
        overwrite_existing = request.get("overwrite_existing", False)

        if not domains:
            raise HTTPException(status_code=400, detail="domains list is required")

        results = role_template_service.apply_template_to_multiple_domains(
            template_name, domains, overwrite_existing
        )

        success_count = sum(
            1 for domain_results in results.values() if "error" not in domain_results
        )

        return {
            "template_name": template_name,
            "domains": domains,
            "results": results,
            "success_count": success_count,
            "total_domains": len(domains),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to apply template {template_name} to multiple domains: {e}"
        )
        raise HTTPException(
            status_code=500, detail="Internal server error while applying template"
        )


@router.post("/templates/{template_name}/add-permission", response_model=dict)
async def add_permission_to_template(template_name: str, request: dict) -> dict:
    """
    Add a permission to a role in a template.

    Request body:
    {
        "role_name": "admin",
        "resource": "reports",
        "action": "read"
    }
    """
    try:
        role_name = request.get("role_name")
        resource = request.get("resource")
        action = request.get("action")

        if not all([role_name, resource, action]):
            raise HTTPException(
                status_code=400, detail="role_name, resource, and action are required"
            )

        success = role_template_service.add_permission_to_template(
            template_name, role_name, resource, action
        )

        if success:
            return {
                "success": True,
                "template_name": template_name,
                "role_name": role_name,
                "resource": resource,
                "action": action,
                "message": f"Permission {action}:{resource} added to role {role_name}",
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to add permission to template '{template_name}'",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add permission to template {template_name}: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error while adding permission"
        )


@router.post("/templates/{template_name}/remove-permission", response_model=dict)
async def remove_permission_from_template(template_name: str, request: dict) -> dict:
    """
    Remove a permission from a role in a template.

    Request body:
    {
        "role_name": "admin",
        "resource": "reports",
        "action": "read"
    }
    """
    try:
        role_name = request.get("role_name")
        resource = request.get("resource")
        action = request.get("action")

        if not all([role_name, resource, action]):
            raise HTTPException(
                status_code=400, detail="role_name, resource, and action are required"
            )

        success = role_template_service.remove_permission_from_template(
            template_name, role_name, resource, action
        )

        if success:
            return {
                "success": True,
                "template_name": template_name,
                "role_name": role_name,
                "resource": resource,
                "action": action,
                "message": f"Permission {action}:{resource} removed from role {role_name}",
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to remove permission from template '{template_name}'",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove permission from template {template_name}: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error while removing permission"
        )


@router.post("/templates/{template_name}/update-and-apply", response_model=dict)
async def update_template_and_apply(template_name: str, request: dict) -> dict:
    """
    Update a template and apply it to multiple domains.

    Request body:
    {
        "updated_config": {
            "roles": {
                "admin": {
                    "permissions": {
                        "users": ["read", "write", "delete", "create"],
                        "documents": ["read", "write", "delete", "create"],
                        "reports": ["read", "write"]
                    }
                }
            }
        },
        "domains": ["tenant-1", "tenant-2", "tenant-3"],
        "overwrite_existing": true
    }
    """
    try:
        updated_config = request.get("updated_config")
        domains = request.get("domains", [])
        overwrite_existing = request.get("overwrite_existing", True)

        if not updated_config or not domains:
            raise HTTPException(
                status_code=400, detail="updated_config and domains are required"
            )

        results = role_template_service.update_template_and_apply(
            template_name, updated_config, domains, overwrite_existing
        )

        success_count = sum(
            1 for domain_results in results.values() if "error" not in domain_results
        )

        return {
            "template_name": template_name,
            "domains": domains,
            "results": results,
            "success_count": success_count,
            "total_domains": len(domains),
            "message": f"Template updated and applied to {success_count}/{len(domains)} domains",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update and apply template {template_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while updating and applying template",
        )
