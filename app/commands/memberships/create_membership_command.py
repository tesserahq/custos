"""Command to create a membership (assign a role to a user)."""

import logging
from typing import Optional, cast
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.role import Role
from app.models.user import User as UserModel
from app.services.membership_service import MembershipService
from app.schemas.authorization import RoleAssignmentResponse
from app.schemas.membership import MembershipCreate
from app.events.membership_events import build_membership_created_event
from tessera_sdk.events.nats_router import NatsEventPublisher
from app.services.user_service import UserService
from app.schemas.user import User
from tessera_sdk import IdentiesClient
from tessera_sdk.utils.m2m_token import M2MTokenClient
from app.config import get_settings
from app.schemas.user import UserOnboard
from app.services.casbin_service import get_casbin_service


class CreateMembershipCommand:
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
        self.user_service = UserService(db)
        self.casbin_service = get_casbin_service()
        self.membership_service = MembershipService(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)
        self.settings = get_settings()

    def execute(
        self,
        role: Role,
        user_id: UUID,
        domain: Optional[str] = None,
        domain_metadata: Optional[dict] = None,
        resource: Optional[str] = None,
        created_by: Optional[UserModel] = None,
    ) -> RoleAssignmentResponse:
        """
        Execute the command to create a role binding.

        Args:
            role: The Role model instance to assign
            user_id: The ID of the user
            domain: The domain/tenant for the role (optional)
            resource: The resource the role applies to (optional)
            created_by: The user performing this action (optional)

        Returns:
            RoleAssignmentResponse: The response containing assignment details

        Raises:
            ValueError: If role assignment fails
        """
        try:
            # Use the role identifier for Casbin
            role_identifier = str(role.identifier)

            # Create membership record. We are keeping a "cache" of memberships in the database. This is not the source of truth.
            # Services using Custos are the source of truth.
            try:
                # Convert user_id string to UUID
                role_uuid = cast(UUID, role.id)

                # Check if membership already exists
                existing_membership = (
                    self.membership_service.get_membership_by_user_and_role(
                        user_id, role_uuid, domain
                    )
                )

                if not existing_membership:
                    # We need to fetch the user from Identies. Users in custos
                    # are being used as a cache for Identies users.
                    # They might might have inconsistent data.
                    user = self.fetch_user(user_id)

                    # Create new membership
                    membership_create = MembershipCreate(
                        user_id=user.id,
                        role_id=role_uuid,
                        domain=domain,
                        domain_metadata=domain_metadata,
                    )
                    self.membership_service.create_membership(membership_create)
                    self.logger.info(
                        f"Membership created: user_id={user_id}, role_id={role_uuid}"
                    )

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

                    # Publish membership created event if publisher is available
                    self._publish_membership_created_event(
                        role, user, domain, resource, created_by
                    )
                else:
                    self.logger.debug(
                        f"Membership already exists: user_id={user_id}, role_id={role_uuid}"
                    )
            except ValueError as e:
                # Handle invalid UUID format
                self.logger.warning(
                    f"Failed to create membership: user_id '{user_id}' is not a valid UUID: {e}"
                )
                # Don't fail the entire operation if membership creation fails
                # The Casbin assignment was successful
            except Exception as e:
                raise ValueError(f"Failed to create membership record: {str(e)}")

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

            return response

        except ValueError:
            # Re-raise ValueError as-is (these are expected validation errors)
            raise
        except Exception as e:
            self.logger.error(f"Failed to assign role: {str(e)}")
            raise ValueError(f"Failed to assign role: {str(e)}")

    def _publish_membership_created_event(
        self,
        role: Role,
        user: User,
        domain: Optional[str],
        resource: Optional[str],
        created_by: Optional[UserModel] = None,
    ) -> None:
        """
        Publish a membership created event.

        Args:
            role: The role that was assigned
            user: The user receiving the role
            domain: The domain/tenant for the membership (optional)
            resource: The resource the membership applies to (optional)
            created_by: The user performing this action (optional)
        """
        event = build_membership_created_event(role, user, domain, resource, created_by)
        if self.nats_publisher is not None:
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to publish membership-created event to NATS"
                )

    def fetch_user(
        self,
        user_id: UUID,
    ) -> User:
        """
        Fetch a user from Identies.

        Args:
            user_id: The ID of the user

        Returns:
            User: The user
        """
        # If the user doesn't exist, we need to fetch it from Identies
        user = self.user_service.get_user(user_id)
        if user:
            return user

        m2m_token = self._get_m2m_token()

        identies_client = IdentiesClient(
            base_url=self.settings.identies_api_url,
            # TODO: This is a temporary solution, we need to move this into jobs
            timeout=320,  # Shorter timeout for middleware
            max_retries=1,  # Fewer retries for middleware
            api_token=m2m_token,
        )

        identies_user = identies_client.get_user(user_id)
        user = UserOnboard(
            id=identies_user.id,
            email=identies_user.email,
            username=identies_user.username,
            service_account=identies_user.service_account,
            first_name=identies_user.first_name,
            last_name=identies_user.last_name,
            avatar_url=identies_user.avatar_url,
            provider=identies_user.provider,
            verified=identies_user.verified,
            verified_at=identies_user.verified_at,
            confirmed_at=identies_user.confirmed_at,
            external_id=identies_user.external_id,
        )

        return self.user_service.onboard_user(user)

    def _get_m2m_token(self) -> str:
        """
        Get an M2M token.
        """
        # TODO: We could change this to use Identies system accounts instead.
        return M2MTokenClient().get_token_sync().access_token
