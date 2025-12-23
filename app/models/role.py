from app.models.mixins import TimestampMixin, SoftDeleteMixin
from sqlalchemy import Column, String, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

import uuid

from app.db import Base


class Role(Base, TimestampMixin, SoftDeleteMixin):
    """Role model for the application.
    This model represents a user in the system and includes fields for
    personal information, authentication, and relationships with other models.
    """

    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    identifier = Column(String, nullable=False)
    description = Column(String, nullable=True)

    permissions = relationship(
        "Permission", back_populates="role", cascade="all, delete-orphan"
    )

    memberships = relationship(
        "Membership", back_populates="role", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "uq_roles_identifier",
            "identifier",
            unique=True,
        ),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
