"""Command to setup system by importing roles and permissions from YAML configuration files."""

import logging
import os
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import yaml

from app.schemas.role import RoleBatchItem, PermissionItem
from app.models.role import Role
from app.commands.role.create_roles_batch_command import CreateRolesBatchCommand
from app.commands.policy.sync_role_policy_command import SyncRolePolicyCommand
from app.commands.binding.create_binding_command import CreateBindingCommand
from app.services.user_service import UserService
from app.config import get_settings
from tessera_sdk.events.nats_router import NatsEventPublisher  # type: ignore


class SetupCommand:
    """
    Command to import roles and permissions from YAML configuration files.
    Validates super_user_email configuration, loads YAML file, transforms data,
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

    def execute(self, yaml_file_path: Optional[str] = None) -> List[Role]:
        """
        Execute the setup command to import roles from YAML file.

        Args:
            yaml_file_path: Path to the YAML file. If None, uses default_roles.yaml
                from app/config directory.

        Returns:
            List[Role]: The created roles

        Raises:
            ValueError: If super_user_email is not configured in settings
            FileNotFoundError: If the YAML file doesn't exist
            ValueError: If the YAML file is invalid or roles already exist
        """
        # Validate that super_user_email is configured
        settings = get_settings()
        super_user_emails = settings.get_super_user_emails()
        if not super_user_emails:
            raise ValueError(
                "System setup requires SUPER_USER_EMAIL to be configured. "
                "Please set the SUPER_USER_EMAIL environment variable."
            )

        if yaml_file_path is None:
            # Default to app/config/default_roles.yaml
            yaml_file_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "config", "default_roles.yaml"
            )

        # Resolve to absolute path
        yaml_file_path = os.path.abspath(yaml_file_path)

        if not os.path.exists(yaml_file_path):
            raise FileNotFoundError(f"YAML file not found: {yaml_file_path}")

        self.logger.info(f"Loading roles from YAML file: {yaml_file_path}")

        # Load YAML file
        with open(yaml_file_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)

        if not yaml_data or "roles" not in yaml_data:
            raise ValueError("YAML file must contain a 'roles' key")

        # Transform YAML data into RoleBatchItem format
        roles_data = self._transform_yaml_to_role_batch_items(yaml_data["roles"])

        # Use CreateRolesBatchCommand to create roles
        command = CreateRolesBatchCommand(self.db, self.nats_publisher)
        created_roles = command.execute(roles_data)

        self.logger.info(
            f"Successfully imported {len(created_roles)} roles from {yaml_file_path}"
        )

        # Bind roles (create policies) and assign to super users
        self._bind_and_assign_roles(created_roles, super_user_emails)

        return created_roles

    def _transform_yaml_to_role_batch_items(
        self, roles_dict: Dict[str, Any]
    ) -> List[RoleBatchItem]:
        """
        Transform YAML roles structure into RoleBatchItem list.

        The YAML structure is:
        ```yaml
        roles:
          role_key:
            name: "Role Name"
            identifier: "role_identifier"
            description: "Role description"
            permissions:
              object1:
                - action1
                - action2
              object2:
                - action3
        ```

        This transforms to RoleBatchItem with flat PermissionItem list.

        Args:
            roles_dict: Dictionary of roles from YAML file

        Returns:
            List[RoleBatchItem]: Transformed role data ready for batch creation
        """
        roles_data = []

        for role_key, role_config in roles_dict.items():
            # Validate required fields
            if "name" not in role_config:
                raise ValueError(f"Role '{role_key}' is missing required field 'name'")
            if "identifier" not in role_config:
                raise ValueError(
                    f"Role '{role_key}' is missing required field 'identifier'"
                )

            # Extract role fields
            name = role_config["name"]
            identifier = role_config["identifier"]
            description = role_config.get("description")

            # Transform permissions from nested structure to flat list
            permissions = []
            if "permissions" in role_config and role_config["permissions"]:
                for object_name, actions in role_config["permissions"].items():
                    if not isinstance(actions, list):
                        raise ValueError(
                            f"Role '{role_key}' permissions for object '{object_name}' "
                            f"must be a list of actions"
                        )
                    for action in actions:
                        permissions.append(
                            PermissionItem(object=object_name, action=action)
                        )

            roles_data.append(
                RoleBatchItem(
                    name=name,
                    identifier=identifier,
                    description=description,
                    permissions=permissions,
                )
            )

        return roles_data

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
            bind_command = CreateBindingCommand(self.db, self.nats_publisher)
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
