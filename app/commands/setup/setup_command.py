"""Command to setup system by importing roles and permissions from JSON configuration files."""

import json
import logging
import os
from typing import List, Optional
from sqlalchemy.orm import Session

from app.schemas.role import RoleBatchItem
from app.models.role import Role
from app.commands.role.create_roles_batch_command import CreateRolesBatchCommand
from app.commands.policy.sync_role_policy_command import SyncRolePolicyCommand
from app.commands.memberships.create_membership_command import CreateMembershipCommand
from app.services.user_service import UserService
from app.config import get_settings
from tessera_sdk.events.nats_router import NatsEventPublisher  # type: ignore


class SetupCommand:
    """
    Command to import roles and permissions from JSON configuration files.
    Validates super_user_email configuration, loads JSON file, transforms data,
    and creates roles using CreateRolesBatchCommand.
    """

    def __init__(
        self,
        db: Session,
        nats_publisher: Optional[NatsEventPublisher] = None,
    ):
        """
        Initialize the setup command.

        Args:
            db: Database session
            nats_publisher: Optional NATS event publisher
        """
        self.db = db
        self.nats_publisher = nats_publisher
        self.logger = logging.getLogger(__name__)
        self.user_service = UserService(db)

    def execute(self, json_file_path: Optional[str] = None) -> List[Role]:
        """
        Execute the setup command to import roles from JSON file.

        Args:
            json_file_path: Path to the JSON file. If None, uses default_roles.json
                from app/config directory.

        Returns:
            List[Role]: The created roles

        Raises:
            ValueError: If super_user_email is not configured in settings
            FileNotFoundError: If the JSON file doesn't exist
            ValueError: If the JSON file is invalid or roles already exist
        """
        # Validate that super_user_email is configured
        settings = get_settings()
        super_user_emails = settings.get_super_user_emails()
        if not super_user_emails:
            raise ValueError(
                "System setup requires SUPER_USER_EMAIL to be configured. "
                "Please set the SUPER_USER_EMAIL environment variable."
            )

        if json_file_path is None:
            # Default to app/config/default_roles.json
            json_file_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "config", "default_roles.json"
            )

        # Resolve to absolute path
        json_file_path = os.path.abspath(json_file_path)

        if not os.path.exists(json_file_path):
            raise FileNotFoundError(f"JSON file not found: {json_file_path}")

        self.logger.info(f"Loading roles from JSON file: {json_file_path}")

        # Load JSON file
        with open(json_file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        if not isinstance(json_data, list):
            raise ValueError("JSON file must contain a list of roles")

        # Parse JSON data directly into RoleBatchItem format
        roles_data = [RoleBatchItem.model_validate(role) for role in json_data]

        # Use CreateRolesBatchCommand to create roles
        command = CreateRolesBatchCommand(self.db, self.nats_publisher)
        created_roles = command.execute(roles_data)

        self.logger.info(
            f"Successfully imported {len(created_roles)} roles from {json_file_path}"
        )

        # Bind roles (create policies) and assign to super users
        self._bind_and_assign_roles(created_roles, super_user_emails)

        return created_roles

    def _bind_and_assign_roles(
        self, created_roles: List[Role], super_user_emails: List[str]
    ) -> None:
        """
        Bind roles (create policies) and assign them to super users.

        Args:
            created_roles: List of roles that were created
            super_user_emails: List of super user email addresses

        Raises:
            ValueError: If a super user email doesn't correspond to an existing user
        """
        # Use "*" as the global domain for system setup
        domain = "*"

        # Look up super users by email
        super_users = []
        for email in super_user_emails:
            user = self.user_service.get_user_by_email(email)
            if not user:
                raise ValueError(
                    f"Super user with email '{email}' not found in database. "
                    "Please ensure the user exists before running setup."
                )
            super_users.append((user, user.id))
            self.logger.info(f"Found super user: {email} (user_id: {user.id})")

        # Bind each role and assign to super users
        policy_command = SyncRolePolicyCommand(self.db)

        for role in created_roles:
            # Bind the role (create policies)
            try:
                from uuid import UUID

                role_id: UUID = role.id  # type: ignore[assignment]
                policy_result = policy_command.execute(role_id, domain)
                self.logger.info(
                    f"Bound role '{role.name}' to domain '{domain}': "
                    f"{policy_result['policies_added']}/{policy_result['total_permissions']} policies created"
                )
            except Exception as e:
                self.logger.warning(
                    f"Failed to bind role '{role.name}' to domain '{domain}': {e}"
                )
                # Continue with role assignment even if binding fails

            # Assign role to each super user
            bind_command = CreateMembershipCommand(self.db, self.nats_publisher)
            for user, user_id in super_users:
                try:
                    response = bind_command.execute(
                        role=role,
                        user_id=str(user_id),
                        domain=domain,
                        resource=None,
                    )
                    if response.success:
                        self.logger.info(
                            f"Assigned role '{role.name}' ({role.identifier}) to user '{user.email}' (user_id: {user_id}) in domain '{domain}'"
                        )
                    else:
                        self.logger.warning(
                            f"Failed to assign role '{role.name}' to user '{user.email}'"
                        )
                except ValueError as e:
                    # Handle validation errors (e.g., role already assigned)
                    self.logger.warning(
                        f"Error assigning role '{role.name}' to user '{user.email}': {e}"
                    )
                    # Continue with other assignments
                except Exception as e:
                    self.logger.warning(
                        f"Error assigning role '{role.name}' to user '{user.email}': {e}"
                    )
                    # Continue with other assignments
