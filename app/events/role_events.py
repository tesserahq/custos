"""Event builders for role-related events."""

from typing import List, Tuple
from app.models.role import Role
from app.models.permission import Permission
from app.schemas.role import Role as RoleSchema
from app.schemas.permission import Permission as PermissionSchema
from tessera_sdk.events.event import Event, event_source, event_type

ROLE_CREATED = "role.created"
ROLE_UPDATED = "role.updated"
ROLE_DELETED = "role.deleted"
ROLES_BATCH_CREATED = "roles.batch.created"


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


def build_roles_batch_created_event(
    created_roles: List[Role], created_permissions: List[Tuple[Role, Permission]]
) -> Event:
    """Create a CloudEvent for batch role and permission creation."""
    # Convert roles to schemas
    roles_data = [
        RoleSchema.model_validate(role).model_dump(mode="json")
        for role in created_roles
    ]

    # Convert permissions to schemas
    permissions_data = [
        PermissionSchema.model_validate(permission).model_dump(mode="json")
        for role, permission in created_permissions
    ]

    return Event(
        source=event_source("/roles/batch"),
        event_type=event_type(ROLES_BATCH_CREATED),
        event_data={
            "privy": True,
            "roles": roles_data,
            "permissions": permissions_data,
            "count": {
                "roles": len(created_roles),
                "permissions": len(created_permissions),
            },
        },
        subject="/roles/batch",
        user_id=None,  # Roles don't have created_by_id in this model
        labels={},
        tags=["batch:roles"],
    )
