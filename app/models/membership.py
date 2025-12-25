from app.models.mixins import TimestampMixin, SoftDeleteMixin
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

import uuid

from app.db import Base


class Membership(Base, TimestampMixin, SoftDeleteMixin):
    """Membership model for the application.
    This model represents the relationship between users and roles in the system.

    It's important to note that memberships are like cache. They might might have inconsistent data.
    """

    __tablename__ = "memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)

    user = relationship("User", back_populates="memberships")
    role = relationship("Role", back_populates="memberships")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
