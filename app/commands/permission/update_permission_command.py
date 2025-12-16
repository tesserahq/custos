"""Command to update a permission."""

import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.permission import Permission
from app.schemas.permission import PermissionUpdate
from app.services.permission_service import PermissionService
from app.events.permission_events import build_permission_updated_event
from tessera_sdk.events.nats_router import NatsEventPublisher


class UpdatePermissionCommand:
    """
    Command to update an existing permission.
    Validates permission exists and uniqueness of object+action+role_id combination, then updates the permission.
    """

    def __init__(
        self,
        db: Session,
        nats_publisher: Optional[NatsEventPublisher] = None,
    ):
        self.db = db
        self.permission_service = PermissionService(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(
        self, permission_id: UUID, permission_data: PermissionUpdate
    ) -> Permission:
        """
        Execute the command to update a permission.

        Args:
            permission_id: The ID of the permission to update
            permission_data: The permission data to update

        Returns:
            Permission: The updated permission

        Raises:
            ValueError: If permission doesn't exist or duplicate object+action+role_id combination
        """
        try:
            # Check if permission exists
            existing_permission = self.permission_service.get_permission(permission_id)
            if not existing_permission:
                raise ValueError(f"Permission with id {permission_id} not found")

            # If object, action, or role_id is being updated, check for duplicates
            object_val = (
                permission_data.object
                if permission_data.object is not None
                else existing_permission.object
            )
            action_val = (
                permission_data.action
                if permission_data.action is not None
                else existing_permission.action
            )
            role_id_val = (
                permission_data.role_id
                if permission_data.role_id is not None
                else existing_permission.role_id
            )

            # Check if the new combination would create a duplicate
            if (
                permission_data.object is not None
                or permission_data.action is not None
                or permission_data.role_id is not None
            ):
                duplicate = self.permission_service.get_permission_by_object_and_action(
                    object_val, action_val, role_id_val
                )
                if duplicate and duplicate.id != permission_id:
                    raise ValueError(
                        f"Permission with object '{object_val}', "
                        f"action '{action_val}', and role_id '{role_id_val}' already exists"
                    )

            # Update permission
            updated_permission = self.permission_service.update_permission(
                permission_id, permission_data
            )

            if not updated_permission:
                raise ValueError(f"Failed to update permission with id {permission_id}")

            # Publish permission updated event if publisher is available
            self._publish_permission_updated_event(updated_permission)

            return updated_permission

        except ValueError:
            # Re-raise ValueError as-is (these are expected validation errors)
            raise
        except Exception as e:
            # Rollback the transaction if something goes wrong
            self.db.rollback()
            raise Exception(f"Failed to update permission: {str(e)}")

    def _publish_permission_updated_event(self, permission: Permission) -> None:
        """
        Publish a permission updated event.

        Args:
            permission: The permission that was updated
        """
        event = build_permission_updated_event(permission)
        if self.nats_publisher is not None:
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to publish permission-updated event to NATS"
                )
