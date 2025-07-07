from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class AuthorizationRequest(BaseModel):
    """Request model for authorization checks."""

    user_id: str = Field(..., description="The ID of the user requesting authorization")
    action: str = Field(
        ..., description="The action being performed (e.g., 'read', 'write', 'delete')"
    )
    resource: str = Field(
        ..., description="The resource being accessed (e.g., 'users', 'documents')"
    )
    domain: Optional[str] = Field(
        None, description="The domain/tenant for multi-tenancy (e.g., account ID)"
    )
    resource_id: Optional[str] = Field(
        None, description="Specific resource ID if applicable"
    )
    context: Optional[Dict[str, Any]] = Field(
        None, description="Additional context for the authorization decision"
    )


class AuthorizationResponse(BaseModel):
    """Response model for authorization decisions."""

    allowed: bool = Field(..., description="Whether the action is allowed")
    user_id: str = Field(..., description="The ID of the user")
    action: str = Field(..., description="The action that was checked")
    resource: str = Field(..., description="The resource that was checked")
    domain: Optional[str] = Field(None, description="The domain/tenant")
    resource_id: Optional[str] = Field(None, description="The specific resource ID")
    reason: Optional[str] = Field(None, description="Reason for the decision if denied")


class RoleAssignmentRequest(BaseModel):
    """Request model for role assignments."""

    user_id: str = Field(..., description="The ID of the user")
    role: str = Field(..., description="The role to assign")
    domain: Optional[str] = Field(None, description="The domain/tenant for the role")
    resource: Optional[str] = Field(
        None, description="The resource the role applies to"
    )


class RoleAssignmentResponse(BaseModel):
    """Response model for role assignments."""

    success: bool = Field(..., description="Whether the role assignment was successful")
    user_id: str = Field(..., description="The ID of the user")
    role: str = Field(..., description="The role that was assigned")
    domain: Optional[str] = Field(None, description="The domain/tenant")
    resource: Optional[str] = Field(
        None, description="The resource the role applies to"
    )
    message: str = Field(..., description="Success or error message")


class PermissionRequest(BaseModel):
    """Request model for permission queries."""

    user_id: str = Field(..., description="The ID of the user")
    domain: Optional[str] = Field(
        None, description="The domain/tenant to check permissions for"
    )
    resource: Optional[str] = Field(
        None, description="The resource to check permissions for"
    )


class PermissionResponse(BaseModel):
    """Response model for permission queries."""

    user_id: str = Field(..., description="The ID of the user")
    domain: Optional[str] = Field(None, description="The domain/tenant")
    permissions: list[str] = Field(..., description="List of permissions the user has")
    roles: list[str] = Field(..., description="List of roles the user has")


class RoleDefinitionRequest(BaseModel):
    """Request model for role definition."""

    role_type: str = Field(
        ...,
        description="Type of role to define: 'admin', 'editor', 'viewer', or 'custom'",
    )
    domain: str = Field(..., description="The domain/tenant for the role")
    role_name: Optional[str] = Field(
        None, description="Custom role name (required for custom role type)"
    )
    custom_permissions: Optional[List[tuple]] = Field(
        None, description="List of (resource, action) tuples for custom roles"
    )


class RoleDefinitionResponse(BaseModel):
    """Response model for role definition."""

    success: bool = Field(..., description="Whether the role definition was successful")
    role_name: str = Field(..., description="The name of the defined role")
    domain: str = Field(..., description="The domain/tenant")
    role_type: str = Field(..., description="The type of role that was defined")
    message: str = Field(..., description="Success or error message")


class RoleListResponse(BaseModel):
    """Response model for role listing."""

    domain: str = Field(..., description="The domain/tenant")
    roles: List[str] = Field(
        ..., description="List of role names defined in the domain"
    )
    count: int = Field(..., description="Number of roles found")
