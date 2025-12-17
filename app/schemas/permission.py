from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class PermissionBase(BaseModel):
    """Base permission model containing common permission attributes."""

    object: str = Field(
        ..., description="The object/resource this permission applies to"
    )
    """Object/resource name. Required field."""

    action: str
    """Action name (e.g., 'read', 'write', 'delete'). Required field."""

    role_id: UUID
    """Role ID this permission belongs to. Required field."""


class PermissionCreate(PermissionBase):
    """Schema for creating a new permission. Inherits all fields from PermissionBase."""

    pass


class PermissionCreateRequest(BaseModel):
    """Schema for creating a permission when role_id comes from the URL path."""

    object: str = Field(
        ..., description="The object/resource this permission applies to"
    )
    """Object/resource name. Required field."""

    action: str
    """Action name (e.g., 'read', 'write', 'delete'). Required field."""


class PermissionUpdate(BaseModel):
    """Schema for updating an existing permission. All fields are optional."""

    object: Optional[str] = Field(None, description="Updated object/resource name")
    """Updated object/resource name."""

    action: Optional[str] = None
    """Updated action name."""

    role_id: Optional[UUID] = None
    """Updated role ID."""


class PermissionInDB(PermissionBase):
    """Schema representing a permission as stored in the database. Includes database-specific fields."""

    id: UUID
    """Unique identifier for the permission in the database."""

    created_at: datetime
    """Timestamp when the permission record was created."""

    updated_at: datetime
    """Timestamp when the permission record was last updated."""

    model_config = {"from_attributes": True}


class Permission(PermissionInDB):
    """Schema for permission data returned in API responses. Inherits all fields from PermissionInDB."""

    pass
