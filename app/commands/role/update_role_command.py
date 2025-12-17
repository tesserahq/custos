"""Command to update a role."""

import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.role import Role
from app.schemas.role import RoleUpdate
from app.services.role_service import RoleService
from app.events.role_events import build_role_updated_event
from tessera_sdk.events.nats_router import NatsEventPublisher


class UpdateRoleCommand:
    """
    Command to update an existing role.
    Validates role exists and name uniqueness, then updates the role.
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

    def execute(self, role_id: UUID, role_data: RoleUpdate) -> Role:
        """
        Execute the command to update a role.

        Args:
            role_id: The ID of the role to update
            role_data: The role data to update

        Returns:
            Role: The updated role

        Raises:
            ValueError: If role doesn't exist or name already exists
        """
        try:
            # Check if role exists
            existing_role = self.role_service.get_role(role_id)
            if not existing_role:
                raise ValueError(f"Role with id {role_id} not found")

            # If name is being updated, check if new name already exists
            if role_data.name is not None and role_data.name != existing_role.name:
                name_conflict = self.role_service.get_role_by_name(role_data.name)
                if name_conflict:
                    raise ValueError(
                        f"Role with name '{role_data.name}' already exists"
                    )

            # Update role
            updated_role = self.role_service.update_role(role_id, role_data)

            if not updated_role:
                raise ValueError(f"Failed to update role with id {role_id}")

            # Publish role updated event if publisher is available
            self._publish_role_updated_event(updated_role)

            return updated_role

        except ValueError:
            # Re-raise ValueError as-is (these are expected validation errors)
            raise
        except Exception as e:
            # Rollback the transaction if something goes wrong
            self.db.rollback()
            raise Exception(f"Failed to update role: {str(e)}")

    def _publish_role_updated_event(self, role: Role) -> None:
        """
        Publish a role updated event.

        Args:
            role: The role that was updated
        """
        event = build_role_updated_event(role)
        if self.nats_publisher is not None:
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception("Failed to publish role-updated event to NATS")
