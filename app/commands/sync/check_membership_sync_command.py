"""Read-only command that compares DB memberships against Casbin g rules for a user."""

import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.membership_repository import MembershipRepository
from app.repositories.casbin_repository import get_casbin_repository
from app.schemas.sync import CasbinBinding, SyncCheckResponse


class CheckMembershipSyncCommand:
    def __init__(self, db: Session):
        self.membership_repository = MembershipRepository(db)
        self.casbin_repository = get_casbin_repository()
        self.logger = logging.getLogger(__name__)

    def execute(self, user_id: str, domain: Optional[str] = None) -> SyncCheckResponse:
        db_bindings = self._get_db_bindings(user_id, domain)
        casbin_bindings = self._get_casbin_bindings(user_id, domain)

        orphan_keys = casbin_bindings - db_bindings
        missing_keys = db_bindings - casbin_bindings

        orphan_list = [
            CasbinBinding(user_id=user_id, role_identifier=ri, domain=d)
            for ri, d in orphan_keys
        ]
        missing_list = [
            CasbinBinding(user_id=user_id, role_identifier=ri, domain=d)
            for ri, d in missing_keys
        ]

        return SyncCheckResponse(
            in_sync=len(orphan_list) == 0 and len(missing_list) == 0,
            orphan_casbin_bindings=orphan_list,
            missing_casbin_bindings=missing_list,
        )

    def _get_db_bindings(self, user_id: str, domain: Optional[str]) -> set:
        """Return a set of (role_identifier, domain) tuples from active DB memberships."""
        memberships = self.membership_repository.get_active_memberships_by_user(
            UUID(user_id), domain
        )
        bindings = set()
        for m in memberships:
            if m.role:
                bindings.add((str(m.role.identifier), m.domain))
            else:
                self.logger.warning(
                    f"Membership {m.id} has no associated role, skipping"
                )
        return bindings

    def _get_casbin_bindings(self, user_id: str, domain: Optional[str]) -> set:
        """Return a set of (role_identifier, domain) tuples from Casbin g rules."""
        if domain is not None:
            roles = self.casbin_repository.get_user_roles(user_id, domain)
            return {(role, domain) for role in roles}

        # When no domain filter, scan all g rules for this user.
        # Each rule is [user_id, role_identifier, domain] or [user_id, role_identifier].
        raw_rules = self.casbin_repository.enforcer.get_filtered_grouping_policy(
            0, user_id
        )
        return {(rule[1], rule[2] if len(rule) > 2 else None) for rule in raw_rules}
