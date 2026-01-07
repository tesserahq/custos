"""Command to create a policy for a permission in a domain."""

import logging
from uuid import UUID
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.services.permission_service import PermissionService
from app.services.casbin_service import get_casbin_service


class AddPermissionPolicyCommand:
    """
    Command to create a policy for a permission in a domain.
    Gets the permission and its associated role, then creates a policy for that permission.
    """

    def __init__(
        self,
        db: Session,
    ):
        self.db = db
        self.permission_service = PermissionService(db)
        self.casbin_service = get_casbin_service()
        self.logger = logging.getLogger(__name__)

    def execute(self, permission_id: UUID, domain: str) -> Dict[str, Any]:
        """
        Execute the command to create a policy for a permission in a domain.

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
                - policy_added: bool indicating if the policy was successfully added

        Raises:
            ValueError: If permission does not exist
        """
        try:
            # Get the permission
            permission = self.permission_service.get_permission(permission_id)
            if not permission:
                raise ValueError(f"Permission with id '{permission_id}' not found")

            # Get the role associated with the permission
            if not permission.role:
                raise ValueError(
                    f"Permission with id '{permission_id}' has no associated role"
                )

            role = permission.role

            # Add policy: subject=role.identifier, domain=domain, obj=permission.object, action=permission.action
            policy_added = self.casbin_service.add_policy(
                subject=role.identifier,
                obj=permission.object,
                action=permission.action,
                domain=domain,
            )

            if policy_added:
                self.logger.debug(
                    f"Policy added: {role.name} -> {permission.object} -> {permission.action} in domain {domain}"
                )
            else:
                self.logger.warning(
                    f"Failed to add policy: {role.name} -> {permission.object} -> {permission.action} in domain {domain}"
                )

            self.logger.info(
                f"Policy {'created' if policy_added else 'failed'} for permission '{permission_id}' "
                f"({permission.object}:{permission.action}) for role '{role.name}' in domain '{domain}'"
            )

            return {
                "success": policy_added,
                "permission_id": str(permission_id),
                "role_name": role.name,
                "object": permission.object,
                "action": permission.action,
                "policy_added": policy_added,
            }

        except ValueError:
            # Re-raise ValueError as-is (these are expected validation errors)
            raise
        except Exception as e:
            self.logger.error(
                f"Failed to create policy for permission {permission_id} in domain {domain}: {e}"
            )
            raise Exception(f"Failed to create policy: {str(e)}")
