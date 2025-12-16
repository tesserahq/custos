"""Event builders for role-related events."""

from app.models.role import Role
from app.schemas.role import Role as RoleSchema
from tessera_sdk.events.event import Event, event_source, event_type

ROLE_CREATED = "role.created"
ROLE_UPDATED = "role.updated"
ROLE_DELETED = "role.deleted"


def build_role_created_event(role: Role) -> Event:
    """Create a CloudEvent for role creation."""
    role_schema = RoleSchema.model_validate(role)

    return Event(
        source=event_source(f"/roles/{role.id}"),
        event_type=event_type(ROLE_CREATED),
        event_data={
            "privy": True,
            "role": role_schema.model_dump(mode="json"),
        },
        subject=f"/role/{role.id}",
        user_id=None,  # Roles don't have created_by_id in this model
        labels={
            "role_id": str(role.id),
        },
        tags=[
            f"role_id:{str(role.id)}",
        ],
    )


def build_role_updated_event(role: Role) -> Event:
    """Create a CloudEvent for role update."""
    role_schema = RoleSchema.model_validate(role)

    return Event(
        source=event_source(f"/roles/{role.id}"),
        event_type=event_type(ROLE_UPDATED),
        event_data={
            "privy": True,
            "role": role_schema.model_dump(mode="json"),
        },
        subject=f"/role/{role.id}",
        user_id=None,  # Roles don't have created_by_id in this model
        labels={
            "role_id": str(role.id),
        },
        tags=[
            f"role_id:{str(role.id)}",
        ],
    )


def build_role_deleted_event(role: Role) -> Event:
    """Create a CloudEvent for role deletion."""
    role_schema = RoleSchema.model_validate(role)

    return Event(
        source=event_source(f"/roles/{role.id}"),
        event_type=event_type(ROLE_DELETED),
        event_data={
            "privy": True,
            "role": role_schema.model_dump(mode="json"),
        },
        subject=f"/role/{role.id}",
        user_id=None,  # Roles don't have created_by_id in this model
        labels={
            "role_id": str(role.id),
        },
        tags=[
            f"role_id:{str(role.id)}",
        ],
    )
