"""Command to create a permission."""

import logging
from typing import Optional, cast
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.permission import Permission
from app.schemas.permission import PermissionCreate
from app.repositories.permission_repository import PermissionRepository
from app.repositories.casbin_repository import GLOBAL_DOMAIN
from app.commands.policy import AddPermissionPolicyCommand
from app.events.permission_events import build_permission_created_event
from app.db import on_commit, savepoint
from tessera_sdk.infra.events.nats_router import NatsEventPublisher


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
        self.permission_repository = PermissionRepository(db)
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
        duplicate_message = (
            f"Permission with object '{permission_data.object}', "
            f"action '{permission_data.action}', and role_id '{permission_data.role_id}' already exists"
        )

        # Check if permission with same object+action+role_id already exists BEFORE creating
        existing = self.permission_repository.get_permission_by_object_and_action(
            permission_data.object,
            permission_data.action,
            permission_data.role_id,
        )
        if existing:
            raise ValueError(duplicate_message)

        try:
            permission = self.permission_repository.create_permission(permission_data)
        except IntegrityError as e:
            # Two requests can pass the check above simultaneously; the unique
            # constraint decides. The caller's rollback discards the failed
            # insert.
            error_str = str(e.orig) if hasattr(e, "orig") else str(e)
            if "unique" in error_str.lower() or "duplicate" in error_str.lower():
                raise ValueError(duplicate_message) from e
            raise

        if not permission:
            raise ValueError("Failed to create permission")

        # Add policy for the permission in the global domain. Best effort: a
        # failure is rolled back to the savepoint and the permission is still
        # created; the policy can be synced later.
        try:
            with savepoint(self.db):
                add_policy_command = AddPermissionPolicyCommand(self.db)
                add_policy_command.execute(cast(UUID, permission.id), GLOBAL_DOMAIN)
        except Exception as e:
            self.logger.warning(
                f"Failed to add policy for permission {permission.id}: {e}. "
                "Permission was created successfully but policy sync failed."
            )

        # Publish permission created event if publisher is available
        self._publish_permission_created_event(permission)

        return permission

    def _publish_permission_created_event(self, permission: Permission) -> None:
        """
        Publish a permission created event.

        Args:
            permission: The permission that was created
        """
        event = build_permission_created_event(permission)
        if self.nats_publisher is not None:
            publisher = self.nats_publisher

            def publish() -> None:
                try:
                    publisher.publish_sync(event, event.event_type)
                except Exception:  # pragma: no cover - defensive logging
                    self.logger.exception(
                        "Failed to publish permission-created event to NATS"
                    )

            # Dispatch only after the transaction commits; dropped on rollback.
            on_commit(publish)
