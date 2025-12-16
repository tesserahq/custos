from app.models.mixins import TimestampMixin, SoftDeleteMixin
from sqlalchemy import Column, ForeignKey, String, Boolean, DateTime, Index, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

import uuid

from app.db import Base


class Permission(Base, TimestampMixin, SoftDeleteMixin):
    """Permission model for the application.
    This model represents a permission in the system and includes fields for
    the object and action.
    """

    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    object = Column(String, nullable=False)
    action = Column(String, nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)

    role = relationship("Role", back_populates="permissions")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
