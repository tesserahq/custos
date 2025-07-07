import pytest
from app.schemas.authorization import (
    AuthorizationRequest,
    RoleAssignmentRequest,
    PermissionRequest,
)


@pytest.fixture
def user_id(setup_user):
    return str(setup_user.id)


def test_authorize_deny_by_default(client, user_id):
    """Should deny access if no policy or role is set."""
    payload = {
        "user_id": user_id,
        "action": "read",
        "resource": "document",
        "domain": "test-domain",
    }
    resp = client.post("/authorization/authorize", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is False
    assert data["reason"] == "Access denied by policy"


def test_assign_role_and_authorize(client, user_id):
    """Assign a role and allow access if policy exists for that role."""
    # Assign role 'reader' to user in domain
    assign_payload = {"user_id": user_id, "role": "reader", "domain": "test-domain"}
    resp = client.post("/authorization/assign-role", json=assign_payload)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Add policy for role 'reader' to allow 'read' on 'document' in domain
    from app.services.casbin_service import casbin_service

    casbin_service.add_policy("reader", "document", "read", domain="test-domain")

    # Now authorize should allow
    auth_payload = {
        "user_id": user_id,
        "action": "read",
        "resource": "document",
        "domain": "test-domain",
    }
    resp = client.post("/authorization/authorize", json=auth_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is True
    assert data["reason"] is None


def test_permissions_endpoint(client, user_id):
    """Test the /permissions endpoint returns roles and permissions."""
    # Assign role and policy
    from app.services.casbin_service import casbin_service

    # Assign role
    role_success = casbin_service.assign_role(user_id, "editor", domain="test-domain")
    print(f"Role assignment success: {role_success}")

    # Add policy (corrected argument order)
    policy_success = casbin_service.add_policy(
        "editor", "document", "edit", domain="test-domain"
    )
    print(f"Policy addition success: {policy_success}")

    # Debug: Check what policies exist
    all_policies = casbin_service.enforcer.get_policy()
    print(f"All policies: {all_policies}")

    # Debug: Check user roles
    user_roles = casbin_service.get_user_roles(user_id, domain="test-domain")
    print(f"User roles: {user_roles}")

    # Debug: Check user permissions directly
    user_permissions = casbin_service.get_user_permissions(
        user_id, domain="test-domain"
    )
    print(f"User permissions: {user_permissions}")

    perm_payload = {"user_id": user_id, "domain": "test-domain"}
    resp = client.post("/authorization/permissions", json=perm_payload)
    assert resp.status_code == 200
    data = resp.json()
    print(f"Response data: {data}")
    assert "editor" in data["roles"]
    assert any("document:edit" in p for p in data["permissions"])
