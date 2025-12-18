"""Event builders for policy-related events."""

from typing import Optional
from tessera_sdk.events.event import Event, event_source, event_type
from app.models.role import Role
from app.schemas.role import Role as RoleSchema

POLICY_CREATED = "policy.created"


def build_policy_created_event(
    role: Role,
    domain: str,
    resource: str,
    action: str,
    role_id: Optional[str] = None,
) -> Event:
    """Create a CloudEvent for policy creation.

    Args:
        role: The role
        domain: The domain/tenant for the policy
        resource: The resource object
        action: The action allowed
        role_id: Optional role ID for labeling

    Returns:
        Event: The policy created event
    """
    role_schema = RoleSchema.model_validate(role)
    policy_data = {
        "role": role_schema.model_dump(mode="json"),
        "domain": domain,
        "object": resource,
        "action": action,
    }

    labels = {
        "role_id": str(role.id),
        "domain": domain,
    }

    tags = [
        f"role_id:{str(role.id)}",
        f"domain:{domain}",
        f"object:{resource}",
        f"action:{action}",
    ]

    if role_id:
        labels["role_id"] = role_id
        tags.append(f"role_id:{role_id}")

    return Event(
        source=event_source(f"/policies/{str(role.id)}/{domain}/{resource}/{action}"),
        event_type=event_type(POLICY_CREATED),
        event_data={
            "privy": True,
            "policy": policy_data,
        },
        subject=f"/policy/{str(role.id)}/{domain}/{resource}/{action}",
        user_id=None,
        labels=labels,
        tags=tags,
    )
