from app.models.mixins import TimestampMixin
from sqlalchemy import Column, String, Boolean, DateTime, Index, text, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

import uuid

from app.db import Base


class ServiceAccount(Base, TimestampMixin):
    """Service Account model for the application.
    This model represents a service account that can be used for API access
    and automation purposes, separate from regular user accounts.
    """

    __tablename__ = "service_accounts"

    __table_args__ = (
        Index(
            "uq_service_accounts_external_id",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
        Index(
            "uq_service_accounts_api_key_hash",
            "api_key_hash",
            unique=True,
            postgresql_where=text("api_key_hash IS NOT NULL"),
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    """Human-readable name for the service account."""

    description = Column(Text, nullable=True)
    """Optional description of the service account's purpose."""

    api_key_hash = Column(String, unique=True, nullable=True)
    """Hashed version of the API key for security. The raw API key is never stored."""

    is_active = Column(Boolean, default=True)
    """Whether the service account is active and can be used."""

    last_used_at = Column(DateTime, nullable=True)
    """Timestamp of the last API usage."""

    expires_at = Column(DateTime, nullable=True)
    """Optional expiration date for the service account."""

    created_by = Column(UUID(as_uuid=True), nullable=True)
    """ID of the user who created this service account."""

    external_id = Column(String, nullable=True)
    """External identifier for integration with other systems."""

    # Note: Permissions are managed through Casbin RBAC system
    # Use the service account ID as a subject in Casbin policies

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def is_expired(self) -> bool:
        """Check if the service account has expired."""
        if not self.expires_at:
            return False
        from datetime import datetime, timezone

        # Handle timezone-aware and timezone-naive datetimes
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at

        # If expires_at is timezone-naive, assume it's UTC
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        return now > expires_at

    def can_be_used(self) -> bool:
        """Check if the service account can be used (active and not expired)."""
        return self.is_active and not self.is_expired()
