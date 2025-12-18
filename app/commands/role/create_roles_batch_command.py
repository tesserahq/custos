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
from app.services.role_service import RoleService
from app.services.permission_service import PermissionService
from app.events.role_events import build_roles_batch_created_event
from tessera_sdk.events.nats_router import NatsEventPublisher  # type: ignore


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
        self.role_service = RoleService(db)
        self.permission_service = PermissionService(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(self, roles_data: List[RoleBatchItem]) -> List[Role]:
        """
        Execute the command to create multiple roles with permissions.

        Args:
            roles_data: List of role data with permissions to create

        Returns:
            List[Role]: The created roles

        Raises:
            ValueError: If any role name already exists or permission already exists
        """
        created_roles = []
        created_permissions = []  # Store (role, permission) tuples for event publishing

        try:
            # Validate all roles and permissions before creating any
            self._validate_batch(roles_data)

            # Create all roles and permissions without committing
            for role_item in roles_data:
                # Check if role identifier already exists
                if self.role_service.get_role_by_identifier(role_item.identifier):
                    raise ValueError(
                        f"Role with identifier '{role_item.identifier}' already exists"
                    )

                # Create role using service (add to session, don't commit yet)
                role_create = RoleCreate(
                    name=role_item.name,
                    identifier=role_item.identifier,
                    description=role_item.description,
                )
                db_role = self.role_service.add_role(role_create)
                self.db.flush()  # Flush to get the role ID without committing

                # Get the role ID as UUID (after flush, id is populated)
                role_id = cast(UUID, db_role.id)

                # Create permissions for this role
                for perm_item in role_item.permissions:
                    # Check if permission already exists
                    existing = (
                        self.permission_service.get_permission_by_object_and_action(
                            perm_item.object,
                            perm_item.action,
                            role_id,
                        )
                    )
                    if existing:
                        raise ValueError(
                            f"Permission with object '{perm_item.object}', "
                            f"action '{perm_item.action}', and role '{role_item.name}' already exists"
                        )

                    # Create permission using service (add to session, don't commit yet)
                    permission_create = PermissionCreate(
                        object=perm_item.object,
                        action=perm_item.action,
                        role_id=role_id,
                    )
                    db_permission = self.permission_service.add_permission(
                        permission_create
                    )
                    created_permissions.append((db_role, db_permission))

                created_roles.append(db_role)

            # Commit all changes in a single transaction
            self.db.commit()

            # Refresh all roles and permissions to get updated timestamps
            for role in created_roles:
                self.db.refresh(role)
            for role, permission in created_permissions:
                self.db.refresh(permission)

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
                "Failed to create roles batch: database constraint violation"
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
                self.logger.info(
                    f"Published batch event for {len(created_roles)} roles and {len(created_permissions)} permissions"
                )
        except Exception:  # pragma: no cover - defensive logging
            self.logger.exception("Failed to publish roles batch-created event to NATS")
