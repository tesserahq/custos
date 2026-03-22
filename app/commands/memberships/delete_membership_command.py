"""Command to delete a membership (remove a role from a user)."""

import logging
from typing import Optional, cast
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.role import Role
from app.repositories.membership_repository import MembershipRepository
from app.schemas.authorization import RoleAssignmentResponse
from app.events.membership_events import build_membership_deleted_event
from tessera_sdk.infra.events.nats_router import NatsEventPublisher
from app.repositories.casbin_repository import get_casbin_repository
from app.models.user import User
from app.repositories.user_repository import UserRepository


class DeleteMembershipCommand:
    """
    Command to delete a membership (remove a role from a user).
    Uses Casbin to remove the role, optionally scoped to a domain and resource.
    """

    def __init__(
        self,
        db: Session,
        nats_publisher: Optional[NatsEventPublisher] = None,
    ):
        self.db = db
        self.casbin_repository = get_casbin_repository()
        self.membership_repository = MembershipRepository(db)
        self.user_repository = UserRepository(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(
        self,
        role: Role,
        user_id: UUID,
        domain: Optional[str] = None,
        resource: Optional[str] = None,
        deleted_by: Optional[User] = None,
    ) -> RoleAssignmentResponse:
        """
        Execute the command to delete a role binding.

        Args:
            role: The Role model instance to remove
            user_id: The ID of the user
            domain: The domain/tenant for the role (optional)
            resource: The resource the role applies to (optional)
            deleted_by: The user performing this action (optional)

        Returns:
            RoleAssignmentResponse: The response containing removal details

        Raises:
            ValueError: If role removal fails
        """
        # We need to fetch the user from Identies. Users in custos
        # are being used as a cache for Identies users.
        # They might might have inconsistent data.
        user = self.user_repository.get_user(user_id)
        if not user:
            raise ValueError(f"User with id '{user_id}' not found")

        # Use the role identifier for Casbin
        role_identifier = str(role.identifier)

        # Remove role from Casbin
        success = self.casbin_repository.remove_role(
            user_id=user_id,
            role=role_identifier,
            domain=domain,
        )

        if not success:
            # Log but don't fail - Casbin removal was successful
            self.logger.error(
                f"Failed to remove role for user {user_id} in domain {domain}. Role may not be assigned or is invalid."
            )

        # Delete membership record
        user_uuid = user_id
        role_uuid = cast(UUID, role.id)

        # Delete membership if it exists (scope by domain when provided)
        deleted = self.membership_repository.delete_membership_by_user_and_role(
            user_uuid, role_uuid, domain=domain
        )

        if not deleted:
            self.logger.error(
                f"Failed to delete membership for user {user_id} in domain {domain}. Membership may not exist or is invalid."
            )

        response = RoleAssignmentResponse(
            success=True,
            user_id=str(user_id),
            role=role_identifier,
            domain=domain,
            resource=resource,
            message=f"Role '{role_identifier}' successfully removed from user '{user_id}'",
        )

        # Publish membership deleted event if publisher is available
        self._publish_membership_deleted_event(role, user, domain, resource, deleted_by)

        return response

    def _publish_membership_deleted_event(
        self,
        role: Role,
        user: User,
        domain: Optional[str],
        resource: Optional[str],
        deleted_by: Optional[User] = None,
    ) -> None:
        """
        Publish a membership deleted event.

        Args:
            role: The role that was removed
            user: The user losing the role
            domain: The domain/tenant for the membership (optional)
            resource: The resource the membership applies to (optional)
            deleted_by: The user performing this action (optional)
        """
        event = build_membership_deleted_event(role, user, domain, resource, deleted_by)
        if self.nats_publisher is not None:
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to publish membership-deleted event to NATS"
                )
