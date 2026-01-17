from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.schemas.user import User
from app.schemas.role import Role


class MembershipBase(BaseModel):
    """Base membership model containing common membership attributes."""

    user_id: UUID
    """User ID. Required field."""

    role_id: UUID
    """Role ID. Required field."""

    domain: Optional[str] = None
    """Domain/tenant for the membership. Optional field."""

    domain_metadata: Optional[dict] = None
    """Metadata for the domain. Optional field."""


class MembershipCreate(MembershipBase):
    """Schema for creating a new membership. Inherits all fields from MembershipBase."""

    pass


class MembershipUpdate(BaseModel):
    """Schema for updating an existing membership. All fields are optional."""

    user_id: Optional[UUID] = None
    """Updated user ID."""

    role_id: Optional[UUID] = None
    """Updated role ID."""


class MembershipInDB(MembershipBase):
    """Schema representing a membership as stored in the database. Includes database-specific fields."""

    id: UUID
    """Unique identifier for the membership in the database."""

    created_at: datetime
    """Timestamp when the membership record was created."""

    updated_at: datetime
    """Timestamp when the membership record was last updated."""

    model_config = {"from_attributes": True}


class Membership(MembershipInDB):
    """Schema for membership data returned in API responses. Inherits all fields from MembershipInDB."""

    user: Optional[User] = None
    """User object associated with this membership. Populated when user relationship is loaded."""

    role: Optional[Role] = None
    """Role object associated with this membership. Populated when role relationship is loaded."""


class MembershipRequest(BaseModel):
    """Request model for role bindings."""

    user_id: str = Field(..., description="The ID of the user")
    domain: Optional[str] = Field(
        default="*", description="The domain/tenant for the role"
    )
    domain_metadata: Optional[dict] = Field(
        None, description="The metadata for the domain"
    )
    resource: Optional[str] = Field(
        None, description="The resource the role applies to"
    )
