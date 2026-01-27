from typing import List, Optional
from uuid import UUID
from sqlalchemy import or_
from sqlalchemy.orm import Session, Query
from app.models.permission import Permission
from app.schemas.permission import PermissionCreate, PermissionUpdate
from app.utils.db.filtering import apply_filters


class PermissionService:
    def __init__(self, db: Session):
        self.db = db

    def get_permission(self, permission_id: UUID) -> Optional[Permission]:
        return self.db.query(Permission).filter(Permission.id == permission_id).first()

    def get_permissions_by_role(self, role_id: UUID) -> List[Permission]:
        return self.db.query(Permission).filter(Permission.role_id == role_id).all()

    def get_permission_by_object_and_action(
        self, object: str, action: str, role_id: UUID
    ) -> Optional[Permission]:
        return (
            self.db.query(Permission)
            .filter(
                Permission.object == object,
                Permission.action == action,
                Permission.role_id == role_id,
            )
            .first()
        )

    def get_permissions(self, skip: int = 0, limit: int = 100) -> List[Permission]:
        return self.db.query(Permission).offset(skip).limit(limit).all()

    def get_permissions_query(self, q: str | None = None) -> Query:
        """
        Get a query object for permissions that can be used with pagination.

        Returns:
            Query: SQLAlchemy query object for permissions.
        """
        query = self.db.query(Permission)

        q_normalized = (q or "").strip()
        if q_normalized:
            # Escape SQL LIKE wildcards so "a_b" doesn't match "acb" etc.
            escaped = (
                q_normalized.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            pattern = f"%{escaped}%"

            query = query.filter(
                or_(
                    Permission.object.ilike(pattern, escape="\\"),
                    Permission.action.ilike(pattern, escape="\\"),
                )
            )

        return query.order_by(Permission.object.asc(), Permission.action.asc())

    def get_permissions_by_role_query(
        self, role_id: UUID, q: str | None = None
    ) -> Query:
        """
        Get a query object for permissions filtered by role_id that can be used with pagination.

        Args:
            role_id: The ID of the role to filter permissions by.
            q: Optional search term to filter permissions by object or action.

        Returns:
            Query: SQLAlchemy query object for permissions filtered by role_id.
        """
        query = self.db.query(Permission).filter(Permission.role_id == role_id)

        q_normalized = (q or "").strip()
        if q_normalized:
            # Escape SQL LIKE wildcards so "a_b" doesn't match "acb" etc.
            escaped = (
                q_normalized.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            pattern = f"%{escaped}%"

            query = query.filter(
                or_(
                    Permission.object.ilike(pattern, escape="\\"),
                    Permission.action.ilike(pattern, escape="\\"),
                )
            )

        return query.order_by(Permission.object.asc(), Permission.action.asc())

    def create_permission(self, permission: PermissionCreate) -> Permission:
        db_permission = Permission(**permission.model_dump())
        self.db.add(db_permission)
        self.db.commit()
        self.db.refresh(db_permission)
        return db_permission

    def add_permission(self, permission: PermissionCreate) -> Permission:
        """
        Add a permission to the session without committing.
        Useful for batch operations where multiple objects need to be created atomically.

        Args:
            permission: The permission data to create

        Returns:
            Permission: The created permission object (not yet committed)
        """
        db_permission = Permission(**permission.model_dump())
        self.db.add(db_permission)
        return db_permission

    def update_permission(
        self, permission_id: UUID, permission: PermissionUpdate
    ) -> Optional[Permission]:
        db_permission = (
            self.db.query(Permission).filter(Permission.id == permission_id).first()
        )
        if db_permission:
            update_data = permission.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_permission, key, value)
            self.db.commit()
            self.db.refresh(db_permission)
        return db_permission

    def delete_permission(self, permission_id: UUID) -> bool:
        db_permission = (
            self.db.query(Permission).filter(Permission.id == permission_id).first()
        )
        if db_permission:
            self.db.delete(db_permission)
            self.db.commit()
            return True
        return False

    def search(self, filters: dict) -> List[Permission]:
        """
        Search permissions based on dynamic filter criteria.

        Args:
            filters: A dictionary where keys are field names and values are either:
                - A direct value (e.g. {"object": "users"})
                - A dictionary with 'operator' and 'value' keys (e.g. {"object": {"operator": "ilike", "value": "%user%"}})

        Returns:
            List[Permission]: Filtered list of permissions matching the criteria.
        """
        query = self.db.query(Permission)
        query = apply_filters(query, Permission, filters)
        return query.all()
