"""Command to create a permission."""

import logging
from typing import Optional, cast
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.permission import Permission
from app.schemas.permission import PermissionCreate
from app.services.permission_service import PermissionService
from app.services.casbin_service import GLOBAL_DOMAIN
from app.commands.policy import AddPermissionPolicyCommand
from app.events.permission_events import build_permission_created_event
from tessera_sdk.events.nats_router import NatsEventPublisher


class CreatePermissionCommand:
    """
    Command to create a new permission.
    Validates uniqueness of object+action+role_id combination, then creates the permission.
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

    def execute(self, permission_data: PermissionCreate) -> Permission:
        """
        Execute the command to create a permission.

        Args:
            permission_data: The permission data to create

        Returns:
            Permission: The created permission

        Raises:
            ValueError: If permission with same object+action+role_id already exists
        """
        try:
            # Check if permission with same object+action+role_id already exists BEFORE creating
            existing = self.permission_service.get_permission_by_object_and_action(
                permission_data.object,
                permission_data.action,
                permission_data.role_id,
            )
            if existing:
                raise ValueError(
                    f"Permission with object '{permission_data.object}', "
                    f"action '{permission_data.action}', and role_id '{permission_data.role_id}' already exists"
                )

            # Create permission (this commits the transaction)
            permission = self.permission_service.create_permission(permission_data)

            if not permission:
                raise ValueError("Failed to create permission")

            # Add policy for the permission in the global domain
            try:
                add_policy_command = AddPermissionPolicyCommand(self.db)
                add_policy_command.execute(cast(UUID, permission.id), GLOBAL_DOMAIN)
            except Exception as e:
                # Log the error but don't fail the permission creation
                # The policy can be synced later if needed
                self.logger.warning(
                    f"Failed to add policy for permission {permission.id}: {e}. "
                    "Permission was created successfully but policy sync failed."
                )

            # Publish permission created event if publisher is available
            self._publish_permission_created_event(permission)

            return permission

        except ValueError:
            # Re-raise ValueError as-is (these are expected validation errors)
            # No rollback needed as no database changes were committed
            raise
        except IntegrityError as e:
            # Handle database-level constraint violations
            # This can happen in race conditions where two requests pass the check simultaneously
            self.db.rollback()
            # Check if it's a duplicate permission error
            error_str = str(e.orig) if hasattr(e, "orig") else str(e)
            if "unique" in error_str.lower() or "duplicate" in error_str.lower():
                raise ValueError(
                    f"Permission with object '{permission_data.object}', "
                    f"action '{permission_data.action}', and role_id '{permission_data.role_id}' already exists"
                )
            raise Exception(
                "Failed to create permission: database constraint violation"
            )
        except Exception as e:
            # Rollback the transaction if something goes wrong
            # This handles cases where create_permission commits but subsequent operations fail
            self.db.rollback()
            raise Exception(f"Failed to create permission: {str(e)}")

    def _publish_permission_created_event(self, permission: Permission) -> None:
        """
        Publish a permission created event.

        Args:
            permission: The permission that was created
        """
        event = build_permission_created_event(permission)
        if self.nats_publisher is not None:
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to publish permission-created event to NATS"
                )
