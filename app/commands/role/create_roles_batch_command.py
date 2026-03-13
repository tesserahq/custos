"""Command to create multiple roles with permissions in a batch."""

import logging
from typing import List, Optional, Tuple, cast
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.role import Role
from app.models.permission import Permission
from app.schemas.role import RoleBatchItem, RoleCreate
from app.schemas.permission import PermissionCreate
from app.repositories.role_repository import RoleRepository
from app.repositories.permission_repository import PermissionRepository
from app.events.role_events import build_roles_batch_created_event
from tessera_sdk.events.nats_router import NatsEventPublisher  # type: ignore
from app.commands.policy.sync_role_policy_command import SyncRolePolicyCommand
from app.repositories.casbin_repository import GLOBAL_DOMAIN


class CreateRolesBatchCommand:
    """
    Command to create multiple roles with their permissions in a single atomic transaction.
    Validates all roles and permissions before creating any, then creates all in one transaction.
    """

    def __init__(
        self,
        db: Session,
        nats_publisher: Optional[NatsEventPublisher] = None,
    ):
        self.db = db
        self.role_repository = RoleRepository(db)
        self.permission_repository = PermissionRepository(db)
        self.sync_role_policy_command = SyncRolePolicyCommand(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(
        self, roles_data: List[RoleBatchItem], resync: bool = False
    ) -> List[Role]:
        """
        Execute the command to create multiple roles with permissions.

        Args:
            roles_data: List of role data with permissions to create
            resync: If True, sync role policies for all roles (new and existing).
                    If False, only sync policies for newly created roles. Defaults to False.

        Returns:
            List[Role]: The created roles

        Raises:
            ValueError: If any role name already exists or permission already exists
        """
        created_roles = []
        newly_created_roles = []  # Track roles that were just created
        created_permissions = []  # Store (role, permission) tuples for event publishing

        try:
            # Validate all roles and permissions before creating any
            self._validate_batch(roles_data)

            # Create all roles and permissions without committing
            for role_item in roles_data:
                # Check if role identifier already exists
                role = self.role_repository.get_role_by_identifier(role_item.identifier)
                is_new_role = False

                if not role:
                    # Create role using service (add to session, don't commit yet)
                    role_create = RoleCreate(
                        name=role_item.name,
                        identifier=role_item.identifier,
                        description=role_item.description,
                    )
                    role = self.role_repository.add_role(role_create)
                    self.db.flush()  # Flush to get the role ID without committing
                    is_new_role = True

                # Get the role ID as UUID (after flush, id is populated)
                role_id = cast(UUID, role.id)

                # Create permissions for this role
                for perm_item in role_item.permissions:
                    # Check if permission already exists
                    existing = (
                        self.permission_repository.get_permission_by_object_and_action(
                            perm_item.object,
                            perm_item.action,
                            role_id,
                        )
                    )
                    if not existing:
                        # Create permission using service (add to session, don't commit yet)
                        permission_create = PermissionCreate(
                            object=perm_item.object,
                            action=perm_item.action,
                            role_id=role_id,
                        )
                        db_permission = self.permission_repository.add_permission(
                            permission_create
                        )
                        created_permissions.append((role, db_permission))

                created_roles.append(role)
                if is_new_role:
                    newly_created_roles.append(role)

            # Commit all changes in a single transaction
            self.db.commit()

            # Refresh all roles and permissions to get updated timestamps
            for role in created_roles:
                self.db.refresh(role)

            # Sync role policies based on resync flag
            roles_to_sync = created_roles if resync else newly_created_roles
            for role in roles_to_sync:
                self.sync_role_policy_command.execute(
                    cast(UUID, role.id), GLOBAL_DOMAIN
                )

            # Publish events for all created roles and permissions
            self._publish_events(created_roles, created_permissions)

            return created_roles

        except ValueError:
            # Re-raise ValueError as-is (these are expected validation errors)
            self.db.rollback()
            raise
        except IntegrityError as e:
            # Handle database-level constraint violations
            self.db.rollback()
            error_str = str(e.orig) if hasattr(e, "orig") else str(e)
            if "name" in error_str.lower() or "unique" in error_str.lower():
                # Try to identify which role caused the issue
                for role_item in roles_data:
                    if self.role_service.get_role_by_name(role_item.name):
                        raise ValueError(
                            f"Role with name '{role_item.name}' already exists"
                        )
                raise ValueError("One or more roles already exist")
            raise Exception(
                "Failed to create roles batch: database constraint violation "
                + error_str
            )
        except Exception as e:
            # Rollback the transaction if something goes wrong
            self.db.rollback()
            raise Exception(f"Failed to create roles batch: {str(e)}")

    def _validate_batch(self, roles_data: List[RoleBatchItem]) -> None:
        """
        Validate all roles and permissions in the batch before creating any.

        Args:
            roles_data: List of role data to validate

        Raises:
            ValueError: If validation fails
        """
        # Check for duplicate role names in the batch itself
        role_names = [role_item.name for role_item in roles_data]
        if len(role_names) != len(set(role_names)):
            duplicates = [name for name in role_names if role_names.count(name) > 1]
            raise ValueError(
                f"Duplicate role names in batch: {', '.join(set(duplicates))}"
            )

    def _publish_events(
        self,
        created_roles: List[Role],
        created_permissions: List[Tuple[Role, Permission]],
    ) -> None:
        """
        Publish a batch event for all created roles and permissions.

        Args:
            created_roles: Created role objects
            created_permissions: List of (role, permission) tuples
        """
        try:
            event = build_roles_batch_created_event(created_roles, created_permissions)
            if self.nats_publisher is not None:
                self.nats_publisher.publish_sync(event, event.event_type)

        except Exception:  # pragma: no cover - defensive logging
            self.logger.exception("Failed to publish roles batch-created event to NATS")
