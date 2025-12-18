"""Command to create policies for a role in a domain."""

import logging
from uuid import UUID
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.role import Role
from app.services.role_service import RoleService
from app.services.casbin_service import CasbinService
from app.events.policy_events import build_policy_created_event
from tessera_sdk.events.nats_router import NatsEventPublisher


class CreatePolicyCommand:
    """
    Command to create policies for a role in a domain.
    Iterates through all permissions associated with the role and adds them as policies.
    """

    def __init__(
        self,
        db: Session,
        nats_publisher: Optional[NatsEventPublisher] = None,
    ):
        self.db = db
        self.role_service = RoleService(db)
        self.casbin_service = CasbinService()
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
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
                    # Publish policy created event
                    self._publish_policy_created_event(
                        role,
                        domain,
                        permission.object,
                        permission.action,
                        role.identifier,
                    )
                else:
                    policies_failed += 1
                    self.logger.warning(
                        f"Failed to add policy: {role.name} -> {permission.object} -> {permission.action} in domain {domain}"
                    )

            # Consider it successful if at least 80% of policies were added
            # This allows for some duplicates while ensuring most policies are created
            success = policies_added >= len(permissions) * 0.8

            self.logger.info(
                f"Policies created for role '{role.name}' (id: {role_id}) in domain '{domain}': "
                f"{policies_added}/{len(permissions)} policies added, {policies_failed} failed"
            )

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

    def _publish_policy_created_event(
        self, role: Role, domain: str, resource: str, action: str, role_id: str
    ) -> None:
        """
        Publish a policy created event.

        Args:
            role_name: The name of the role
            domain: The domain/tenant for the policy
            resource: The resource object
            action: The action allowed
            role_id: The role ID
        """
        event = build_policy_created_event(role, domain, resource, action, role_id)
        if self.nats_publisher is not None:
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception("Failed to publish policy-created event to NATS")
