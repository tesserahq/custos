"""Command to create a role."""

import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.role import Role
from app.schemas.role import RoleCreate
from app.services.role_service import RoleService
from app.events.role_events import build_role_created_event
from tessera_sdk.events.nats_router import NatsEventPublisher


class CreateRoleCommand:
    """
    Command to create a new role.
    Validates uniqueness of name, then creates the role.
    """

    def __init__(
        self,
        db: Session,
        nats_publisher: Optional[NatsEventPublisher] = None,
    ):
        self.db = db
        self.role_service = RoleService(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(self, role_data: RoleCreate) -> Role:
        """
        Execute the command to create a role.

        Args:
            role_data: The role data to create

        Returns:
            Role: The created role

        Raises:
            ValueError: If role name already exists
        """
        try:
            # Check if role name already exists BEFORE creating
            if self.role_service.get_role_by_name(role_data.name):
                raise ValueError(f"Role with name '{role_data.name}' already exists")

            # Create role (this commits the transaction)
            role = self.role_service.create_role(role_data)

            if not role:
                raise ValueError("Failed to create role")

            # Publish role created event if publisher is available
            self._publish_role_created_event(role)

            return role

        except ValueError:
            # Re-raise ValueError as-is (these are expected validation errors)
            # No rollback needed as no database changes were committed
            raise
        except IntegrityError as e:
            # Handle database-level constraint violations (e.g., unique constraint on name)
            # This can happen in race conditions where two requests pass the check simultaneously
            self.db.rollback()
            # Check if it's a duplicate name error
            error_str = str(e.orig) if hasattr(e, "orig") else str(e)
            if "name" in error_str.lower() or "unique" in error_str.lower():
                raise ValueError(f"Role with name '{role_data.name}' already exists")
            raise Exception("Failed to create role: database constraint violation")
        except Exception as e:
            # Rollback the transaction if something goes wrong
            # This handles cases where create_role commits but subsequent operations fail
            self.db.rollback()
            raise Exception(f"Failed to create role: {str(e)}")

    def _publish_role_created_event(self, role: Role) -> None:
        """
        Publish a role created event.

        Args:
            role: The role that was created
        """
        event = build_role_created_event(role)
        if self.nats_publisher is not None:
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception("Failed to publish role-created event to NATS")
