"""Event builders for role binding-related events."""

from typing import Optional
from app.models.role import Role
from app.schemas.role import Role as RoleSchema
from tessera_sdk.events.event import Event, event_source, event_type

BIND_CREATED = "bind.created"


def build_bind_created_event(
    role: Role,
    user_id: str,
    domain: Optional[str] = None,
    resource: Optional[str] = None,
) -> Event:
    """Create a CloudEvent for role binding creation.

    Args:
        role: The role being assigned
        user_id: The ID of the user receiving the role
        domain: The domain/tenant for the binding (optional)
        resource: The resource the binding applies to (optional)

    Returns:
        Event: The bind created event
    """
    role_schema = RoleSchema.model_validate(role)
    bind_data = {
        "role": role_schema.model_dump(mode="json"),
        "user_id": user_id,
    }

    if domain:
        bind_data["domain"] = domain
    if resource:
        bind_data["resource"] = resource

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

    source_path = f"/binds/{str(role.id)}/{user_id}"
    if domain:
        source_path += f"/{domain}"
    if resource:
        source_path += f"/{resource}"

    subject_path = f"/bind/{str(role.id)}/{user_id}"
    if domain:
        subject_path += f"/{domain}"
    if resource:
        subject_path += f"/{resource}"

    return Event(
        source=event_source(source_path),
        event_type=event_type(BIND_CREATED),
        event_data={
            "privy": True,
            "bind": bind_data,
        },
        subject=subject_path,
        user_id=user_id,
        labels=labels,
        tags=tags,
    )
