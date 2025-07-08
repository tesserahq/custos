from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class ServiceAccountBase(BaseModel):
    """Base service account model containing common attributes."""

    name: str = Field(..., min_length=1, max_length=255)
    """Human-readable name for the service account. Required field."""

    description: Optional[str] = Field(None, max_length=1000)
    """Optional description of the service account's purpose."""

    is_active: bool = True
    """Whether the service account is active and can be used. Defaults to True."""

    expires_at: Optional[datetime] = None
    """Optional expiration date for the service account."""

    external_id: Optional[str] = None
    """External identifier for integration with other systems."""

    # Note: Permissions are managed through Casbin RBAC system


class ServiceAccountCreate(ServiceAccountBase):
    """Schema for creating a new service account. Inherits all fields from ServiceAccountBase."""

    api_key: Optional[str] = None
    """Optional API key. If not provided, one will be generated automatically."""


class ServiceAccountUpdate(BaseModel):
    """Schema for updating an existing service account. All fields are optional."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    """Updated name for the service account."""

    description: Optional[str] = Field(None, max_length=1000)
    """Updated description."""

    is_active: Optional[bool] = None
    """Updated active status."""

    expires_at: Optional[datetime] = None
    """Updated expiration date."""

    external_id: Optional[str] = None
    """Updated external identifier."""

    # Note: Permissions are managed through Casbin RBAC system


class ServiceAccountInDB(ServiceAccountBase):
    """Schema representing a service account as stored in the database. Includes database-specific fields."""

    id: UUID
    """Unique identifier for the service account in the database."""

    api_key_hash: Optional[str] = None
    """Hashed version of the API key for security."""

    last_used_at: Optional[datetime] = None
    """Timestamp of the last API usage."""

    created_by: Optional[UUID] = None
    """ID of the user who created this service account."""

    created_at: datetime
    """Timestamp when the service account record was created."""

    updated_at: datetime
    """Timestamp when the service account record was last updated."""

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


class ServiceAccount(ServiceAccountInDB):
    """Schema for service account data returned in API responses. Inherits all fields from ServiceAccountInDB."""

    pass


class ServiceAccountWithKey(ServiceAccountInDB):
    """Schema for service account data including the API key (only used during creation)."""

    api_key: Optional[str] = None
    """The API key for the service account. Only included during creation."""

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


class ServiceAccountDetails(BaseModel):
    """Schema for detailed service account information."""

    id: UUID
    """Unique identifier for the service account."""

    name: str
    """Human-readable name for the service account."""

    description: Optional[str] = None
    """Description of the service account's purpose."""

    is_active: bool
    """Whether the service account is active."""

    last_used_at: Optional[datetime] = None
    """Timestamp of the last API usage."""

    expires_at: Optional[datetime] = None
    """Expiration date for the service account."""

    created_by: Optional[UUID] = None
    """ID of the user who created this service account."""

    external_id: Optional[str] = None
    """External identifier for integration."""

    # Note: Permissions are managed through Casbin RBAC system

    class Config:
        """Pydantic model configuration."""

        from_attributes = True
