from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class RoleBase(BaseModel):
    """Base role model containing common role attributes."""

    name: str
    """Role name. Required field."""

    identifier: str
    """Role identifier. Required field."""

    description: Optional[str] = None
    """Role description. Optional field."""


class RoleCreate(RoleBase):
    """Schema for creating a new role. Inherits all fields from RoleBase."""

    pass


class RoleUpdate(BaseModel):
    """Schema for updating an existing role. All fields are optional."""

    name: Optional[str] = None
    """Updated role name."""

    identifier: Optional[str] = None
    """Updated role identifier. Required field."""

    description: Optional[str] = None
    """Updated role description."""


class RoleInDB(RoleBase):
    """Schema representing a role as stored in the database. Includes database-specific fields."""

    id: UUID
    """Unique identifier for the role in the database."""

    identifier: str
    """Role identifier. Required field."""

    created_at: datetime
    """Timestamp when the role record was created."""

    updated_at: datetime
    """Timestamp when the role record was last updated."""

    model_config = {"from_attributes": True}


class Role(RoleInDB):
    """Schema for role data returned in API responses. Inherits all fields from RoleInDB."""

    pass


class PermissionItem(BaseModel):
    """Schema for a permission item in batch role creation."""

    object: str
    """Object/resource name. Required field."""

    action: str
    """Action name (e.g., 'read', 'write', 'delete'). Required field."""


class RoleBatchItem(BaseModel):
    """Schema for a single role in batch creation."""

    name: str
    """Role name. Required field."""

    identifier: Optional[str] = None
    """Role identifier. Required field."""

    description: Optional[str] = None
    """Role description. Optional field."""

    permissions: List[PermissionItem]
    """List of permissions for this role. Required field."""


class RoleBatchRequest(BaseModel):
    """Schema for batch role creation request."""

    resync: bool = False
    """If True, sync role policies for all roles (new and existing).
    If False, only sync policies for newly created roles. Defaults to False."""

    roles: List[RoleBatchItem]
    """List of roles with permissions to create. Required field."""


class RoleBindRequest(BaseModel):
    """Schema for binding a role to a domain by creating policies."""

    domain: str
    """Domain/tenant for the policies. Required field."""


class RoleBindResponse(BaseModel):
    """Schema for the response when binding a role to a domain."""

    success: bool
    """Whether the binding operation was successful."""

    role_name: str
    """Name of the role that was bound."""

    total_permissions: int
    """Total number of permissions associated with the role."""

    policies_added: int
    """Number of policies successfully added."""

    policies_failed: int
    """Number of policies that failed to be added."""
