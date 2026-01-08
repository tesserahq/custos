"""Event builders for membership-related events."""

from typing import Optional
from app.models.role import Role
from app.schemas.role import Role as RoleSchema
from tessera_sdk.events.event import Event, event_source, event_type

MEMBERSHIP_CREATED = "membership.created"
MEMBERSHIP_DELETED = "membership.deleted"


def build_membership_created_event(
    role: Role,
    user_id: str,
    domain: Optional[str] = None,
    resource: Optional[str] = None,
) -> Event:
    """Create a CloudEvent for membership creation.

    Args:
        role: The role being assigned
        user_id: The ID of the user receiving the role
        domain: The domain/tenant for the membership (optional)
        resource: The resource the membership applies to (optional)

    Returns:
        Event: The membership created event
    """
    role_schema = RoleSchema.model_validate(role)
    membership_data = {
        "role": role_schema.model_dump(mode="json"),
        "user_id": user_id,
    }

    if domain:
        membership_data["domain"] = domain
    if resource:
        membership_data["resource"] = resource

    labels = {
        "role_id": str(role.id),
        "user_id": user_id,
    }

    tags = [
        f"role_id:{str(role.id)}",
        f"user_id:{user_id}",
    ]

    if domain:
        labels["domain"] = domain
        tags.append(f"domain:{domain}")

    if resource:
        labels["resource"] = resource
        tags.append(f"resource:{resource}")

    source_path = f"/memberships/{str(role.id)}/{user_id}"
    if domain:
        source_path += f"/{domain}"
    if resource:
        source_path += f"/{resource}"

    subject_path = f"/membership/{str(role.id)}/{user_id}"
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
        user_id=user_id,
        labels=labels,
        tags=tags,
    )


def build_membership_deleted_event(
    role: Role,
    user_id: str,
    domain: Optional[str] = None,
    resource: Optional[str] = None,
) -> Event:
    """Create a CloudEvent for membership deletion.

    Args:
        role: The role being removed
        user_id: The ID of the user losing the role
        domain: The domain/tenant for the membership (optional)
        resource: The resource the membership applies to (optional)

    Returns:
        Event: The membership deleted event
    """
    role_schema = RoleSchema.model_validate(role)
    membership_data = {
        "role": role_schema.model_dump(mode="json"),
        "user_id": user_id,
    }

    if domain:
        membership_data["domain"] = domain
    if resource:
        membership_data["resource"] = resource

    labels = {
        "role_id": str(role.id),
        "user_id": user_id,
    }

    tags = [
        f"role_id:{str(role.id)}",
        f"user_id:{user_id}",
    ]

    if domain:
        labels["domain"] = domain
        tags.append(f"domain:{domain}")

    if resource:
        labels["resource"] = resource
        tags.append(f"resource:{resource}")

    source_path = f"/memberships/{str(role.id)}/{user_id}"
    if domain:
        source_path += f"/{domain}"
    if resource:
        source_path += f"/{resource}"

    subject_path = f"/membership/{str(role.id)}/{user_id}"
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
        user_id=user_id,
        labels=labels,
        tags=tags,
    )
