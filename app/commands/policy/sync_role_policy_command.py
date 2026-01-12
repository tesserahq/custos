"""Command to create policies for a role in a domain."""

import logging
from uuid import UUID
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.services.role_service import RoleService
from app.services.casbin_service import get_casbin_service


class SyncRolePolicyCommand:
    """
    Command to create policies for a role in a domain.
    Iterates through all permissions associated with the role and adds them as policies.
    """

    def __init__(
        self,
        db: Session,
    ):
        self.db = db
        self.role_service = RoleService(db)
        self.casbin_service = get_casbin_service()
        self.logger = logging.getLogger(__name__)

    def execute(self, role_id: UUID, domain: str) -> Dict[str, Any]:
        """
        Execute the command to create policies for a role in a domain.

        Args:
            role_id: The ID of the role
            domain: The domain/tenant for the policies

        Returns:
            Dict containing:
                - success: bool indicating overall success
                - role_name: str name of the role
                - total_permissions: int total number of permissions
                - policies_added: int number of policies successfully added
                - policies_failed: int number of policies that failed to add

        Raises:
            ValueError: If role does not exist
        """
        try:
            # Get the role
            role = self.role_service.get_role(role_id)
            if not role:
                raise ValueError(f"Role with id '{role_id}' not found")

            # Get all permissions for the role
            permissions = role.permissions
            if not permissions:
                self.logger.warning(
                    f"Role '{role.name}' (id: {role_id}) has no permissions to create policies for"
                )
                return {
                    "success": True,
                    "role_name": role.name,
                    "total_permissions": 0,
                    "policies_added": 0,
                    "policies_failed": 0,
                }

            # Add policies for each permission
            policies_added = 0
            policies_failed = 0

            for permission in permissions:
                # Add policy: subject=role.name, domain=domain, obj=permission.object, action=permission.action
                if self.casbin_service.add_policy(
                    subject=role.identifier,
                    obj=permission.object,
                    action=permission.action,
                    domain=domain,
                ):
                    policies_added += 1
                    self.logger.debug(
                        f"Policy added: {role.name} -> {permission.object} -> {permission.action} in domain {domain}"
                    )

                else:
                    policies_failed += 1
                    self.logger.warning(
                        f"Failed to add policy: {role.name} -> {permission.object} -> {permission.action} in domain {domain}"
                    )

            # Consider it successful if at least 80% of policies were added
            # This allows for some duplicates while ensuring most policies are created
            success = policies_added >= len(permissions) * 0.8

            return {
                "success": success,
                "role_name": role.name,
                "total_permissions": len(permissions),
                "policies_added": policies_added,
                "policies_failed": policies_failed,
            }

        except ValueError:
            # Re-raise ValueError as-is (these are expected validation errors)
            raise
        except Exception as e:
            self.logger.error(
                f"Failed to create policies for role {role_id} in domain {domain}: {e}"
            )
            raise Exception(f"Failed to create policies: {str(e)}")
