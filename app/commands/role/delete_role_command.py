"""Command to delete a role."""

import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.role import Role
from app.services.role_service import RoleService
from app.events.role_events import build_role_deleted_event
from tessera_sdk.events.nats_router import NatsEventPublisher


class DeleteRoleCommand:
    """
    Command to delete an existing role.
    Validates role exists, then deletes it and publishes an event.
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

    def execute(self, role_id: UUID) -> bool:
        """
        Execute the command to delete a role.

        Args:
            role_id: The ID of the role to delete

        Returns:
            bool: True if the role was deleted, False otherwise

        Raises:
            ValueError: If role doesn't exist
        """
        try:
            # Get the role before deleting it (for event publishing)
            role = self.role_service.get_role(role_id)
            if not role:
                raise ValueError(f"Role with id {role_id} not found")

            # Delete role
            success = self.role_service.delete_role(role_id)

            if not success:
                raise ValueError(f"Failed to delete role with id {role_id}")

            # Publish role deleted event if publisher is available
            # Note: We publish the event after deletion, using the role data we fetched before deletion
            self._publish_role_deleted_event(role)

            return success

        except ValueError:
            # Re-raise ValueError as-is (these are expected validation errors)
            raise
        except Exception as e:
            # Rollback the transaction if something goes wrong
            self.db.rollback()
            raise Exception(f"Failed to delete role: {str(e)}")

    def _publish_role_deleted_event(self, role: Role) -> None:
        """
        Publish a role deleted event.

        Args:
            role: The role that was deleted (fetched before deletion)
        """
        event = build_role_deleted_event(role)
        if self.nats_publisher is not None:
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception("Failed to publish role-deleted event to NATS")
