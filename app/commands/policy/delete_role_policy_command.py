"""Command to delete all policies for a role in Casbin."""

import logging
from uuid import UUID
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.repositories.role_repository import RoleRepository
from app.repositories.casbin_repository import get_casbin_repository


class DeleteRolePolicyCommand:
    """
    Command to delete all policies for a role in Casbin.
    Removes all policies where the subject matches the role identifier across all domains.
    """

    def __init__(
        self,
        db: Session,
    ):
        self.db = db
        self.role_repository = RoleRepository(db)
        self.casbin_repository = get_casbin_repository()
        self.logger = logging.getLogger(__name__)

    def execute(self, role_id: UUID) -> Dict[str, Any]:
        """
        Execute the command to delete all policies for a role.

        Args:
            role_id: The ID of the role

        Returns:
            Dict containing:
                - success: bool indicating overall success
                - role_name: str name of the role
                - policies_removed: int number of policies successfully removed

        Raises:
            ValueError: If role does not exist
        """
        try:
            # Get the role
            role = self.role_repository.get_role(role_id)
            if not role:
                raise ValueError(f"Role with id '{role_id}' not found")

            role_identifier = str(role.identifier)

            # Remove all policies for this role across all domains
            policies_removed = self.casbin_repository.remove_all_policies_for_role(
                role_identifier
            )

            if policies_removed > 0:
                self.logger.debug(
                    f"Removed {policies_removed} policies for role '{role.name}' (identifier: {role_identifier})"
                )
            else:
                self.logger.debug(
                    f"No policies found for role '{role.name}' (identifier: {role_identifier})"
                )

            return {
                "success": True,
                "role_name": role.name,
                "policies_removed": policies_removed,
            }

        except ValueError:
            # Re-raise ValueError as-is (these are expected validation errors)
            raise
        except Exception as e:
            self.logger.error(f"Failed to remove policies for role {role_id}: {e}")
            raise Exception(f"Failed to remove policies: {str(e)}")
