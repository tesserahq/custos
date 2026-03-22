"""Command to delete a permission."""

import logging
from typing import Optional, cast
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.permission import Permission
from app.repositories.permission_repository import PermissionRepository
from app.repositories.casbin_repository import GLOBAL_DOMAIN
from app.commands.policy import DeletePermissionPolicyCommand
from app.events.permission_events import build_permission_deleted_event
from tessera_sdk.infra.events.nats_router import NatsEventPublisher


class DeletePermissionCommand:
    """
    Command to delete an existing permission.
    Validates permission exists, then deletes it and publishes an event.
    """

    def __init__(
        self,
        db: Session,
        nats_publisher: Optional[NatsEventPublisher] = None,
    ):
        self.db = db
        self.permission_repository = PermissionRepository(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(self, permission_id: UUID) -> bool:
        """
        Execute the command to delete a permission.

        Args:
            permission_id: The ID of the permission to delete

        Returns:
            bool: True if the permission was deleted, False otherwise

        Raises:
            ValueError: If permission doesn't exist
        """
        try:
            # Get the permission before deleting it (for event publishing and policy removal)
            permission = self.permission_repository.get_permission(permission_id)
            if not permission:
                raise ValueError(f"Permission with id {permission_id} not found")

            # Remove policy for the permission in the global domain before deleting
            try:
                delete_policy_command = DeletePermissionPolicyCommand(self.db)
                delete_policy_command.execute(cast(UUID, permission.id), GLOBAL_DOMAIN)
            except Exception as e:
                # Log the error but don't fail the permission deletion
                # The policy may not exist or may have already been removed
                self.logger.warning(
                    f"Failed to remove policy for permission {permission.id}: {e}. "
                    "Permission will still be deleted from database."
                )

            # Delete permission
            success = self.permission_repository.delete_permission(permission_id)

            if not success:
                raise ValueError(f"Failed to delete permission with id {permission_id}")

            # Publish permission deleted event if publisher is available
            # Note: We publish the event after deletion, using the permission data we fetched before deletion
            self._publish_permission_deleted_event(permission)

            return success

        except ValueError:
            # Re-raise ValueError as-is (these are expected validation errors)
            raise
        except Exception as e:
            # Rollback the transaction if something goes wrong
            self.db.rollback()
            raise Exception(f"Failed to delete permission: {str(e)}")

    def _publish_permission_deleted_event(self, permission: Permission) -> None:
        """
        Publish a permission deleted event.

        Args:
            permission: The permission that was deleted (fetched before deletion)
        """
        event = build_permission_deleted_event(permission)
        if self.nats_publisher is not None:
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to publish permission-deleted event to NATS"
                )
