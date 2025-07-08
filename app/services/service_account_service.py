from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.service_account import ServiceAccount
from app.schemas.service_account import (
    ServiceAccountCreate,
    ServiceAccountUpdate,
    ServiceAccountWithKey,
)
from datetime import datetime, timezone
import secrets
import hashlib
import json

from app.utils.db.filtering import apply_filters


class ServiceAccountService:
    def __init__(self, db: Session):
        self.db = db

    def get_service_account(self, service_account_id: UUID) -> Optional[ServiceAccount]:
        """Get a service account by ID."""
        return (
            self.db.query(ServiceAccount)
            .filter(ServiceAccount.id == service_account_id)
            .first()
        )

    def get_service_account_by_api_key(self, api_key: str) -> Optional[ServiceAccount]:
        """Get a service account by API key."""
        api_key_hash = self._hash_api_key(api_key)
        return (
            self.db.query(ServiceAccount)
            .filter(ServiceAccount.api_key_hash == api_key_hash)
            .first()
        )

    def get_service_account_by_external_id(
        self, external_id: str
    ) -> Optional[ServiceAccount]:
        """Get a service account by external ID."""
        return (
            self.db.query(ServiceAccount)
            .filter(ServiceAccount.external_id == external_id)
            .first()
        )

    def get_service_accounts(
        self, skip: int = 0, limit: int = 100
    ) -> List[ServiceAccount]:
        """Get a list of service accounts with pagination."""
        return self.db.query(ServiceAccount).offset(skip).limit(limit).all()

    def create_service_account(
        self, service_account: ServiceAccountCreate, created_by: Optional[UUID] = None
    ) -> ServiceAccountWithKey:
        """
        Create a new service account and return a ServiceAccountWithKey schema instance.
        The api_key is only returned at creation and is not stored in the database.
        """
        # Generate API key if not provided
        api_key = service_account.api_key or self._generate_api_key()

        # Create the service account data
        service_account_data = service_account.model_dump(exclude={"api_key"})
        service_account_data["api_key_hash"] = self._hash_api_key(api_key)
        service_account_data["created_by"] = created_by

        # Permissions are managed through Casbin RBAC system

        db_service_account = ServiceAccount(**service_account_data)
        self.db.add(db_service_account)
        self.db.commit()
        self.db.refresh(db_service_account)

        # Return a ServiceAccountWithKey schema instance
        return ServiceAccountWithKey(**db_service_account.__dict__, api_key=api_key)

    def update_service_account(
        self, service_account_id: UUID, service_account: ServiceAccountUpdate
    ) -> Optional[ServiceAccount]:
        """Update an existing service account."""
        db_service_account = (
            self.db.query(ServiceAccount)
            .filter(ServiceAccount.id == service_account_id)
            .first()
        )
        if db_service_account:
            update_data = service_account.model_dump(exclude_unset=True)

            # Permissions are managed through Casbin RBAC system

            for key, value in update_data.items():
                setattr(db_service_account, key, value)

            self.db.commit()
            self.db.refresh(db_service_account)
        return db_service_account

    def delete_service_account(self, service_account_id: UUID) -> bool:
        """Delete a service account."""
        db_service_account = (
            self.db.query(ServiceAccount)
            .filter(ServiceAccount.id == service_account_id)
            .first()
        )
        if db_service_account:
            self.db.delete(db_service_account)
            self.db.commit()
            return True
        return False

    def regenerate_api_key(
        self, service_account_id: UUID
    ) -> Optional[ServiceAccountWithKey]:
        """Regenerate the API key for a service account and return a ServiceAccountWithKey schema instance."""
        db_service_account = (
            self.db.query(ServiceAccount)
            .filter(ServiceAccount.id == service_account_id)
            .first()
        )
        if db_service_account:
            new_api_key = self._generate_api_key()
            db_service_account.api_key_hash = self._hash_api_key(new_api_key)
            self.db.commit()
            self.db.refresh(db_service_account)
            return ServiceAccountWithKey(
                **db_service_account.__dict__, api_key=new_api_key
            )
        return None

    def update_last_used(self, service_account_id: UUID) -> Optional[ServiceAccount]:
        """Update the last used timestamp for a service account."""
        db_service_account = (
            self.db.query(ServiceAccount)
            .filter(ServiceAccount.id == service_account_id)
            .first()
        )
        if db_service_account:
            db_service_account.last_used_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(db_service_account)
        return db_service_account

    def deactivate_service_account(
        self, service_account_id: UUID
    ) -> Optional[ServiceAccount]:
        """Deactivate a service account."""
        db_service_account = (
            self.db.query(ServiceAccount)
            .filter(ServiceAccount.id == service_account_id)
            .first()
        )
        if db_service_account:
            db_service_account.is_active = False
            self.db.commit()
            self.db.refresh(db_service_account)
        return db_service_account

    def activate_service_account(
        self, service_account_id: UUID
    ) -> Optional[ServiceAccount]:
        """Activate a service account."""
        db_service_account = (
            self.db.query(ServiceAccount)
            .filter(ServiceAccount.id == service_account_id)
            .first()
        )
        if db_service_account:
            db_service_account.is_active = True
            self.db.commit()
            self.db.refresh(db_service_account)
        return db_service_account

    def search(self, filters: dict) -> List[ServiceAccount]:
        """
        Search service accounts based on dynamic filter criteria.

        Args:
            filters: A dictionary where keys are field names and values are either:
                - A direct value (e.g. {"name": "test-service"})
                - A dictionary with 'operator' and 'value' keys (e.g. {"name": {"operator": "ilike", "value": "%test%"}})

        Returns:
            List[ServiceAccount]: Filtered list of service accounts matching the criteria.
        """
        query = self.db.query(ServiceAccount)
        query = apply_filters(query, ServiceAccount, filters)
        return query.all()

    def get_active_service_accounts(self) -> List[ServiceAccount]:
        """Get all active service accounts."""
        return (
            self.db.query(ServiceAccount).filter(ServiceAccount.is_active == True).all()
        )

    def get_expired_service_accounts(self) -> List[ServiceAccount]:
        """Get all expired service accounts."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        return (
            self.db.query(ServiceAccount)
            .filter(
                ServiceAccount.expires_at.isnot(None), ServiceAccount.expires_at < now
            )
            .all()
        )

    def _generate_api_key(self) -> str:
        """Generate a secure API key."""
        return f"sk_{secrets.token_urlsafe(32)}"

    def _hash_api_key(self, api_key: str) -> str:
        """Hash an API key for secure storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def assign_role(
        self, service_account_id: UUID, role: str, domain: Optional[str] = None
    ) -> bool:
        """Assign a role to a service account using Casbin."""
        from app.services.casbin_service import CasbinService

        casbin_service = CasbinService()
        return casbin_service.assign_role(str(service_account_id), role, domain)

    def remove_role(
        self, service_account_id: UUID, role: str, domain: Optional[str] = None
    ) -> bool:
        """Remove a role from a service account using Casbin."""
        from app.services.casbin_service import CasbinService

        casbin_service = CasbinService()
        return casbin_service.remove_role(str(service_account_id), role, domain)

    def get_roles(
        self, service_account_id: UUID, domain: Optional[str] = None
    ) -> List[str]:
        """Get all roles assigned to a service account using Casbin."""
        from app.services.casbin_service import CasbinService

        casbin_service = CasbinService()
        return casbin_service.get_user_roles(str(service_account_id), domain)

    def get_permissions(
        self, service_account_id: UUID, domain: Optional[str] = None
    ) -> List[Tuple[str, ...]]:
        """Get all permissions for a service account using Casbin."""
        from app.services.casbin_service import CasbinService

        casbin_service = CasbinService()
        return casbin_service.get_user_permissions(str(service_account_id), domain)

    def authorize(
        self,
        service_account_id: UUID,
        action: str,
        resource: str,
        domain: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> bool:
        """Check if a service account is authorized to perform an action using Casbin."""
        from app.services.casbin_service import CasbinService

        casbin_service = CasbinService()
        return casbin_service.authorize(
            str(service_account_id), action, resource, domain, resource_id
        )
