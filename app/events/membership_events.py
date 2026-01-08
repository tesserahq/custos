"""Event builders for membership-related events."""

from typing import Optional
from app.models.role import Role
from app.models.user import User as UserModel
from app.schemas.role import Role as RoleSchema
from tessera_sdk.events.event import Event, event_source, event_type
from app.schemas.user import User
from app.schemas.user import User as UserSchema

MEMBERSHIP_CREATED = "membership.created"
MEMBERSHIP_DELETED = "membership.deleted"


def build_membership_created_event(
    role: Role,
    user: User,
    domain: Optional[str] = None,
    resource: Optional[str] = None,
    created_by: Optional[UserModel] = None,
) -> Event:
    """Create a CloudEvent for membership creation.

    Args:
        role: The role being assigned
        user: The user receiving the role
        domain: The domain/tenant for the membership (optional)
        resource: The resource the membership applies to (optional)
        created_by: The user performing this action (optional)

    Returns:
        Event: The membership created event
    """
    role_schema = RoleSchema.model_validate(role)
    user_schema = UserSchema.model_validate(user)
    membership_data = {
        "role": role_schema.model_dump(mode="json"),
        "user": user_schema.model_dump(mode="json"),
    }

    if created_by:
        created_by_schema = UserSchema.model_validate(created_by)
        membership_data["created_by"] = created_by_schema.model_dump(mode="json")

    if domain:
        membership_data["domain"] = domain
    if resource:
        membership_data["resource"] = resource

    labels = {
        "role_id": str(role.id),
        "user_id": str(user.id),
    }

    tags = [
        f"role_id:{str(role.id)}",
        f"user_id:{str(user.id)}",
    ]

    if created_by:
        labels["created_by_user_id"] = str(created_by.id)
        tags.append(f"created_by_user_id:{str(created_by.id)}")

    if domain:
        labels["domain"] = domain
        tags.append(f"domain:{domain}")

    if resource:
        labels["resource"] = resource
        tags.append(f"resource:{resource}")

    source_path = f"/memberships/{str(role.id)}/{str(user.id)}"
    if domain:
        source_path += f"/{domain}"
    if resource:
        source_path += f"/{resource}"

    subject_path = f"/membership/{str(role.id)}/{str(user.id)}"
    if domain:
        subject_path += f"/{domain}"
    if resource:
        subject_path += f"/{resource}"

    return Event(
        source=event_source(source_path),
        event_type=event_type(MEMBERSHIP_CREATED),
        event_data={
            "privy": True,
            "membership": membership_data,
        },
        subject=subject_path,
        user_id=str(user.id),
        labels=labels,
        tags=tags,
    )


def build_membership_deleted_event(
    role: Role,
    user: User,
    domain: Optional[str] = None,
    resource: Optional[str] = None,
    deleted_by: Optional[UserModel] = None,
) -> Event:
    """Create a CloudEvent for membership deletion.

    Args:
        role: The role being removed
        user: The user losing the role
        domain: The domain/tenant for the membership (optional)
        resource: The resource the membership applies to (optional)
        deleted_by: The user performing this action (optional)

    Returns:
        Event: The membership deleted event
    """
    role_schema = RoleSchema.model_validate(role)
    user_schema = UserSchema.model_validate(user)
    membership_data = {
        "role": role_schema.model_dump(mode="json"),
        "user": user_schema.model_dump(mode="json"),
    }

    if deleted_by:
        deleted_by_schema = UserSchema.model_validate(deleted_by)
        membership_data["deleted_by"] = deleted_by_schema.model_dump(mode="json")

    if domain:
        membership_data["domain"] = domain
    if resource:
        membership_data["resource"] = resource

    labels = {
        "role_id": str(role.id),
        "user_id": str(user.id),
    }

    tags = [
        f"role_id:{str(role.id)}",
        f"user_id:{str(user.id)}",
    ]

    if deleted_by:
        labels["deleted_by_user_id"] = str(deleted_by.id)
        tags.append(f"deleted_by_user_id:{str(deleted_by.id)}")

    if domain:
        labels["domain"] = domain
        tags.append(f"domain:{domain}")

    if resource:
        labels["resource"] = resource
        tags.append(f"resource:{resource}")

    source_path = f"/memberships/{str(role.id)}/{str(user.id)}"
    if domain:
        source_path += f"/{domain}"
    if resource:
        source_path += f"/{resource}"

    subject_path = f"/membership/{str(role.id)}/{str(user.id)}"
    if domain:
        subject_path += f"/{domain}"
    if resource:
        subject_path += f"/{resource}"

    return Event(
        source=event_source(source_path),
        event_type=event_type(MEMBERSHIP_DELETED),
        event_data={
            "privy": True,
            "membership": membership_data,
        },
        subject=subject_path,
        user_id=str(user.id),
        labels=labels,
        tags=tags,
    )
