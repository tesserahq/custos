from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session, Query, joinedload
from app.models.membership import Membership
from app.schemas.membership import MembershipCreate, MembershipUpdate
from app.utils.db.filtering import apply_filters


class MembershipService:
    def __init__(self, db: Session):
        self.db = db

    def get_membership(self, membership_id: UUID) -> Optional[Membership]:
        """Get a membership by ID with user relationship loaded."""
        return (
            self.db.query(Membership)
            .options(joinedload(Membership.user))
            .filter(Membership.id == membership_id)
            .first()
        )

    def get_memberships_by_user(self, user_id: UUID) -> List[Membership]:
        """Get all memberships for a specific user with user relationship loaded."""
        return (
            self.db.query(Membership)
            .options(joinedload(Membership.user))
            .filter(Membership.user_id == user_id)
            .all()
        )

    def get_memberships_by_role(self, role_id: UUID) -> List[Membership]:
        """Get all memberships for a specific role with user relationship loaded."""
        return (
            self.db.query(Membership)
            .options(joinedload(Membership.user))
            .filter(Membership.role_id == role_id)
            .all()
        )

    def get_membership_by_user_and_role(
        self, user_id: UUID, role_id: UUID, domain: Optional[str] = None
    ) -> Optional[Membership]:
        """Get a membership by user ID and role ID with user relationship loaded."""
        return (
            self.db.query(Membership)
            .options(joinedload(Membership.user))
            .filter(
                Membership.user_id == user_id,
                Membership.role_id == role_id,
                Membership.domain == domain,
            )
            .first()
        )

    def get_memberships(self, skip: int = 0, limit: int = 100) -> List[Membership]:
        """Get a list of memberships with pagination and user relationship loaded."""
        return (
            self.db.query(Membership)
            .options(joinedload(Membership.user))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_memberships_query(self) -> Query:
        """
        Get a query object for memberships that can be used with pagination.
        Includes user relationship loaded.

        Returns:
            Query: SQLAlchemy query object for memberships with user relationship loaded.
        """
        return self.db.query(Membership).options(joinedload(Membership.user))

    def get_memberships_by_user_query(self, user_id: UUID) -> Query:
        """
        Get a query object for memberships by user_id that can be used with pagination.
        Includes user and role relationships loaded.

        Args:
            user_id: The UUID of the user to filter memberships by

        Returns:
            Query: SQLAlchemy query object for memberships filtered by user_id with user and role relationships loaded.
        """
        return (
            self.db.query(Membership)
            .options(joinedload(Membership.user), joinedload(Membership.role))
            .filter(Membership.user_id == user_id)
        )

    def create_membership(self, membership: MembershipCreate) -> Membership:
        """Create a new membership."""
        db_membership = Membership(**membership.model_dump())
        self.db.add(db_membership)
        self.db.commit()
        self.db.refresh(db_membership)
        return db_membership

    def add_membership(self, membership: MembershipCreate) -> Membership:
        """
        Add a membership to the session without committing.
        Useful for batch operations where multiple objects need to be created atomically.

        Args:
            membership: The membership data to create

        Returns:
            Membership: The created membership object (not yet committed)
        """
        db_membership = Membership(**membership.model_dump())
        self.db.add(db_membership)
        return db_membership

    def update_membership(
        self, membership_id: UUID, membership: MembershipUpdate
    ) -> Optional[Membership]:
        """Update an existing membership."""
        db_membership = (
            self.db.query(Membership).filter(Membership.id == membership_id).first()
        )
        if db_membership:
            update_data = membership.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_membership, key, value)
            self.db.commit()
            self.db.refresh(db_membership)
        return db_membership

    def delete_membership(self, membership_id: UUID) -> bool:
        """Delete a membership by ID."""
        db_membership = (
            self.db.query(Membership).filter(Membership.id == membership_id).first()
        )
        if db_membership:
            self.db.delete(db_membership)
            self.db.commit()
            return True
        return False

    def delete_membership_by_user_and_role(self, user_id: UUID, role_id: UUID) -> bool:
        """Delete a membership by user ID and role ID."""
        db_membership = self.get_membership_by_user_and_role(user_id, role_id)
        if db_membership:
            self.db.delete(db_membership)
            self.db.commit()
            return True
        return False

    def search(self, filters: dict) -> List[Membership]:
        """
        Search memberships based on dynamic filter criteria with user relationship loaded.

        Args:
            filters: A dictionary where keys are field names and values are either:
                - A direct value (e.g. {"user_id": "123e4567-e89b-12d3-a456-426614174000"})
                - A dictionary with 'operator' and 'value' keys (e.g. {"user_id": {"operator": "eq", "value": "123e4567-e89b-12d3-a456-426614174000"}})

        Returns:
            List[Membership]: Filtered list of memberships matching the criteria with user relationship loaded.
        """
        query = self.db.query(Membership).options(joinedload(Membership.user))
        query = apply_filters(query, Membership, filters)
        return query.all()
