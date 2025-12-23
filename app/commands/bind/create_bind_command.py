"""Command to create a role binding (assign a role to a user)."""

import logging
from typing import Optional, cast
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.role import Role
from app.services.casbin_service import CasbinService
from app.services.membership_service import MembershipService
from app.schemas.authorization import RoleAssignmentResponse
from app.schemas.membership import MembershipCreate
from app.events.bind_events import build_bind_created_event
from tessera_sdk.events.nats_router import NatsEventPublisher


class CreateBindCommand:
    """
    Command to create a role binding (assign a role to a user).
    Uses Casbin to assign the role, optionally scoped to a domain and resource.
    """

    def __init__(
        self,
        db: Session,
        nats_publisher: Optional[NatsEventPublisher] = None,
    ):
        self.db = db
        self.casbin_service = CasbinService()
        self.membership_service = MembershipService(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(
        self,
        role: Role,
        user_id: str,
        domain: Optional[str] = None,
        resource: Optional[str] = None,
    ) -> RoleAssignmentResponse:
        """
        Execute the command to create a role binding.

        Args:
            role: The Role model instance to assign
            user_id: The ID of the user
            domain: The domain/tenant for the role (optional)
            resource: The resource the role applies to (optional)

        Returns:
            RoleAssignmentResponse: The response containing assignment details

        Raises:
            ValueError: If role assignment fails
        """
        try:
            # Use the role identifier for Casbin
            role_identifier = str(role.identifier)

            # Assign role
            success = self.casbin_service.assign_role(
                user_id=user_id,
                role=role_identifier,
                domain=domain,
                resource=resource,
            )

            if not success:
                raise ValueError(
                    "Failed to assign role. Role may already exist or be invalid."
                )

            # Create membership record
            try:
                # Convert user_id string to UUID
                user_uuid = UUID(user_id)
                role_uuid = cast(UUID, role.id)

                # Check if membership already exists
                existing_membership = (
                    self.membership_service.get_membership_by_user_and_role(
                        user_uuid, role_uuid
                    )
                )

                if not existing_membership:
                    # Create new membership
                    membership_create = MembershipCreate(
                        user_id=user_uuid,
                        role_id=role_uuid,
                    )
                    self.membership_service.create_membership(membership_create)
                    self.logger.info(
                        f"Membership created: user_id={user_uuid}, role_id={role_uuid}"
                    )
                else:
                    self.logger.debug(
                        f"Membership already exists: user_id={user_uuid}, role_id={role_uuid}"
                    )
            except ValueError as e:
                # Handle invalid UUID format
                self.logger.warning(
                    f"Failed to create membership: user_id '{user_id}' is not a valid UUID: {e}"
                )
                # Don't fail the entire operation if membership creation fails
                # The Casbin assignment was successful
            except Exception as e:
                # Log but don't fail - Casbin assignment was successful
                self.logger.error(f"Failed to create membership record: {str(e)}")

            response = RoleAssignmentResponse(
                success=True,
                user_id=user_id,
                role=role_identifier,
                domain=domain,
                resource=resource,
                message=f"Role '{role_identifier}' successfully assigned to user '{user_id}'",
            )

            self.logger.info(
                f"Role assigned: user={user_id}, role={role_identifier}, "
                f"domain={domain}, resource={resource}"
            )

            # Publish bind created event if publisher is available
            self._publish_bind_created_event(role, user_id, domain, resource)

            return response

        except ValueError:
            # Re-raise ValueError as-is (these are expected validation errors)
            raise
        except Exception as e:
            self.logger.error(f"Failed to assign role: {str(e)}")
            raise ValueError(f"Failed to assign role: {str(e)}")

    def _publish_bind_created_event(
        self,
        role: Role,
        user_id: str,
        domain: Optional[str],
        resource: Optional[str],
    ) -> None:
        """
        Publish a bind created event.

        Args:
            role: The role that was assigned
            user_id: The ID of the user receiving the role
            domain: The domain/tenant for the binding (optional)
            resource: The resource the binding applies to (optional)
        """
        event = build_bind_created_event(role, user_id, domain, resource)
        if self.nats_publisher is not None:
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception("Failed to publish bind-created event to NATS")
