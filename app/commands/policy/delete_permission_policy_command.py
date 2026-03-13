"""Command to delete a policy for a permission in a domain."""

import logging
from uuid import UUID
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.repositories.permission_repository import PermissionRepository
from app.repositories.casbin_repository import get_casbin_repository


class DeletePermissionPolicyCommand:
    """
    Command to delete a policy for a permission in a domain.
    Gets the permission and its associated role, then removes the policy for that permission.
    """

    def __init__(
        self,
        db: Session,
    ):
        self.db = db
        self.permission_repository = PermissionRepository(db)
        self.casbin_repository = get_casbin_repository()
        self.logger = logging.getLogger(__name__)

    def execute(self, permission_id: UUID, domain: str) -> Dict[str, Any]:
        """
        Execute the command to delete a policy for a permission in a domain.

        Args:
            permission_id: The ID of the permission
            domain: The domain/tenant for the policy

        Returns:
            Dict containing:
                - success: bool indicating overall success
                - permission_id: str ID of the permission
                - role_name: str name of the associated role
                - object: str object of the permission
                - action: str action of the permission
                - policy_removed: bool indicating if the policy was successfully removed

        Raises:
            ValueError: If permission does not exist
        """
        try:
            # Get the permission
            permission = self.permission_repository.get_permission(permission_id)
            if not permission:
                raise ValueError(f"Permission with id '{permission_id}' not found")

            # Get the role associated with the permission
            if not permission.role:
                raise ValueError(
                    f"Permission with id '{permission_id}' has no associated role"
                )

            role = permission.role

            # Remove policy: subject=role.identifier, domain=domain, obj=permission.object, action=permission.action
            policy_removed = self.casbin_repository.remove_policy(
                subject=role.identifier,
                obj=permission.object,
                action=permission.action,
                domain=domain,
            )

            if policy_removed:
                self.logger.debug(
                    f"Policy removed: {role.name} -> {permission.object} -> {permission.action} in domain {domain}"
                )
            else:
                self.logger.warning(
                    f"Failed to remove policy: {role.name} -> {permission.object} -> {permission.action} in domain {domain}. "
                    "Policy may not exist."
                )

            return {
                "success": policy_removed,
                "permission_id": str(permission_id),
                "role_name": role.name,
                "object": permission.object,
                "action": permission.action,
                "policy_removed": policy_removed,
            }

        except ValueError:
            # Re-raise ValueError as-is (these are expected validation errors)
            raise
        except Exception as e:
            self.logger.error(
                f"Failed to remove policy for permission {permission_id} in domain {domain}: {e}"
            )
            raise Exception(f"Failed to remove policy: {str(e)}")
