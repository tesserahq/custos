from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class RoleBase(BaseModel):
    """Base role model containing common role attributes."""

    name: str
    """Role name. Required field."""

    description: Optional[str] = None
    """Role description. Optional field."""


class RoleCreate(RoleBase):
    """Schema for creating a new role. Inherits all fields from RoleBase."""

    pass


class RoleUpdate(BaseModel):
    """Schema for updating an existing role. All fields are optional."""

    name: Optional[str] = None
    """Updated role name."""

    description: Optional[str] = None
    """Updated role description."""


class RoleInDB(RoleBase):
    """Schema representing a role as stored in the database. Includes database-specific fields."""

    id: UUID
    """Unique identifier for the role in the database."""

    created_at: datetime
    """Timestamp when the role record was created."""

    updated_at: datetime
    """Timestamp when the role record was last updated."""

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


class Role(RoleInDB):
    """Schema for role data returned in API responses. Inherits all fields from RoleInDB."""

    pass
