"""Event builders for permission-related events."""

from app.models.permission import Permission
from app.schemas.permission import Permission as PermissionSchema
from tessera_sdk.infra.events.event import Event, event_source, event_type

PERMISSION_CREATED = "permission.created"
PERMISSION_UPDATED = "permission.updated"
PERMISSION_DELETED = "permission.deleted"


def build_permission_created_event(permission: Permission) -> Event:
    """Create a CloudEvent for permission creation."""
    permission_schema = PermissionSchema.model_validate(permission)

    return Event(
        source=event_source(f"/permissions/{permission.id}"),
        event_type=event_type(PERMISSION_CREATED),
        event_data={
            "privy": True,
            "permission": permission_schema.model_dump(mode="json"),
        },
        subject=f"/permission/{permission.id}",
        user_id=None,  # Permissions don't have created_by_id in this model
        labels={
            "permission_id": str(permission.id),
            "role_id": str(permission.role_id),
        },
        tags=[
            f"permission_id:{str(permission.id)}",
            f"role_id:{str(permission.role_id)}",
        ],
    )


def build_permission_updated_event(permission: Permission) -> Event:
    """Create a CloudEvent for permission update."""
    permission_schema = PermissionSchema.model_validate(permission)

    return Event(
        source=event_source(f"/permissions/{permission.id}"),
        event_type=event_type(PERMISSION_UPDATED),
        event_data={
            "privy": True,
            "permission": permission_schema.model_dump(mode="json"),
        },
        subject=f"/permission/{permission.id}",
        user_id=None,  # Permissions don't have created_by_id in this model
        labels={
            "permission_id": str(permission.id),
            "role_id": str(permission.role_id),
        },
        tags=[
            f"permission_id:{str(permission.id)}",
            f"role_id:{str(permission.role_id)}",
        ],
    )


def build_permission_deleted_event(permission: Permission) -> Event:
    """Create a CloudEvent for permission deletion."""
    permission_schema = PermissionSchema.model_validate(permission)

    return Event(
        source=event_source(f"/permissions/{permission.id}"),
        event_type=event_type(PERMISSION_DELETED),
        event_data={
            "privy": True,
            "permission": permission_schema.model_dump(mode="json"),
        },
        subject=f"/permission/{permission.id}",
        user_id=None,  # Permissions don't have created_by_id in this model
        labels={
            "permission_id": str(permission.id),
            "role_id": str(permission.role_id),
        },
        tags=[
            f"permission_id:{str(permission.id)}",
            f"role_id:{str(permission.role_id)}",
        ],
    )
