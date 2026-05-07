"""Command that reconciles Casbin g rules to match DB memberships (DB is source of truth)."""

import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.casbin_repository import get_casbin_repository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.events.membership_events import (
    build_membership_created_event,
    build_membership_deleted_event,
)
from tessera_sdk.infra.events.nats_router import NatsEventPublisher
from app.commands.sync.check_membership_sync_command import CheckMembershipSyncCommand
from app.schemas.sync import CasbinBinding, SyncFixResponse


class FixMembershipSyncCommand:
    def __init__(
        self, db: Session, nats_publisher: Optional[NatsEventPublisher] = None
    ):
        self.db = db
        self.casbin_repository = get_casbin_repository()
        self.role_repository = RoleRepository(db)
        self.user_repository = UserRepository(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(self, user_id: str, domain: Optional[str] = None) -> SyncFixResponse:
        check = CheckMembershipSyncCommand(self.db)
        result = check.execute(user_id, domain)

        user = self.user_repository.get_user(UUID(user_id))

        removed: list[CasbinBinding] = []
        added: list[CasbinBinding] = []
        events_published = 0

        for binding in result.orphan_casbin_bindings:
            self.casbin_repository.remove_role(
                binding.user_id, binding.role_identifier, binding.domain
            )
            removed.append(binding)
            events_published += self._publish_deleted(binding, user)

        for binding in result.missing_casbin_bindings:
            self.casbin_repository.assign_role(
                binding.user_id, binding.role_identifier, binding.domain
            )
            added.append(binding)
            events_published += self._publish_created(binding, user)

        return SyncFixResponse(
            removed_from_casbin=removed,
            added_to_casbin=added,
            events_published=events_published,
        )

    def _publish_deleted(self, binding: CasbinBinding, user) -> int:
        role = self.role_repository.get_role_by_identifier(binding.role_identifier)
        if not role or not user:
            return 0
        event = build_membership_deleted_event(role, user, binding.domain)
        return self._publish(event)

    def _publish_created(self, binding: CasbinBinding, user) -> int:
        role = self.role_repository.get_role_by_identifier(binding.role_identifier)
        if not role or not user:
            return 0
        event = build_membership_created_event(role, user, binding.domain)
        return self._publish(event)

    def _publish(self, event) -> int:
        if self.nats_publisher is not None:
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
                return 1
            except Exception:
                self.logger.exception("Failed to publish sync event to NATS")
        return 0
