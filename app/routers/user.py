from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.user_service import UserService
from app.services.membership_service import MembershipService
from app.schemas.user import User
from app.schemas.membership import Membership
from uuid import UUID
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from app.routers.utils.dependencies import get_user_by_id


router = APIRouter(prefix="/users", tags=["User"])


@router.get("/", response_model=Page[User])
def list_users(db: Session = Depends(get_db)) -> Page[User]:
    """
    List all users with pagination.

    Returns a paginated response using fastapi-pagination.
    """
    user_service = UserService(db)
    query = user_service.get_users_query()
    return paginate(query)


@router.get("/{user_id}", response_model=User)
def get_user(user: User = Depends(get_user_by_id)) -> User:
    """
    Retrieve a specific user by ID.

    Raises 404 if the user is not found.
    """
    return user


@router.get("/{user_id}/memberships", response_model=Page[Membership])
def list_user_memberships(
    user: User = Depends(get_user_by_id), db: Session = Depends(get_db)
) -> Page[Membership]:
    """
    List all memberships for a specific user with pagination.

    Raises 404 if the user is not found.
    Returns a paginated response using fastapi-pagination.
    """
    membership_service = MembershipService(db)
    query = membership_service.get_memberships_by_user_query(user.id)
    return paginate(query)
