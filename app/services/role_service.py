from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session, Query
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate
from app.utils.db.filtering import apply_filters


class RoleService:
    def __init__(self, db: Session):
        self.db = db

    def get_role(self, role_id: UUID) -> Optional[Role]:
        return self.db.query(Role).filter(Role.id == role_id).first()

    def get_role_by_name(self, name: str) -> Optional[Role]:
        return self.db.query(Role).filter(Role.name == name).first()

    def get_roles(self, skip: int = 0, limit: int = 100) -> List[Role]:
        return self.db.query(Role).offset(skip).limit(limit).all()

    def get_roles_query(self) -> Query:
        """
        Get a query object for roles that can be used with pagination.

        Returns:
            Query: SQLAlchemy query object for roles.
        """
        return self.db.query(Role)

    def create_role(self, role: RoleCreate) -> Role:
        db_role = Role(**role.model_dump())
        self.db.add(db_role)
        self.db.commit()
        self.db.refresh(db_role)
        return db_role

    def update_role(self, role_id: UUID, role: RoleUpdate) -> Optional[Role]:
        db_role = self.db.query(Role).filter(Role.id == role_id).first()
        if db_role:
            update_data = role.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_role, key, value)
            self.db.commit()
            self.db.refresh(db_role)
        return db_role

    def delete_role(self, role_id: UUID) -> bool:
        db_role = self.db.query(Role).filter(Role.id == role_id).first()
        if db_role:
            self.db.delete(db_role)
            self.db.commit()
            return True
        return False

    def search(self, filters: dict) -> List[Role]:
        """
        Search roles based on dynamic filter criteria.

        Args:
            filters: A dictionary where keys are field names and values are either:
                - A direct value (e.g. {"name": "admin"})
                - A dictionary with 'operator' and 'value' keys (e.g. {"name": {"operator": "ilike", "value": "%admin%"}})

        Returns:
            List[Role]: Filtered list of roles matching the criteria.
        """
        query = self.db.query(Role)
        query = apply_filters(query, Role, filters)
        return query.all()
