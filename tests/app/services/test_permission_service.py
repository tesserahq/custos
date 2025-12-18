from uuid import uuid4
from app.schemas.permission import PermissionCreate, PermissionUpdate
from app.services.permission_service import PermissionService


def test_create_permission(db, setup_role, faker):
    """Test creating a new permission."""
    # Create permission
    permission_data = {
        "object": faker.word().lower(),
        "action": faker.word().lower(),
        "role_id": setup_role.id,
    }
    permission_create = PermissionCreate(**permission_data)
    permission = PermissionService(db).create_permission(permission_create)

    # Assertions
    assert permission.id is not None
    assert permission.object == permission_data["object"]
    assert permission.action == permission_data["action"]
    assert permission.role_id == permission_data["role_id"]
    assert permission.created_at is not None
    assert permission.updated_at is not None


def test_get_permission(db, setup_permission):
    """Test retrieving a permission by ID."""
    # Get permission
    retrieved_permission = PermissionService(db).get_permission(setup_permission.id)

    # Assertions
    assert retrieved_permission is not None
    assert retrieved_permission.id == setup_permission.id
    assert retrieved_permission.object == setup_permission.object
    assert retrieved_permission.action == setup_permission.action
    assert retrieved_permission.role_id == setup_permission.role_id


def test_get_permissions_by_role(db, setup_role, setup_permission):
    """Test retrieving permissions by role ID."""
    # Get permissions by role
    permissions = PermissionService(db).get_permissions_by_role(setup_role.id)

    # Assertions
    assert len(permissions) >= 1
    assert any(p.id == setup_permission.id for p in permissions)


def test_get_permission_by_object_and_action(db, setup_permission):
    """Test retrieving a permission by object, action, and role."""
    # Get permission by object and action
    retrieved_permission = PermissionService(db).get_permission_by_object_and_action(
        setup_permission.object,
        setup_permission.action,
        setup_permission.role_id,
    )

    # Assertions
    assert retrieved_permission is not None
    assert retrieved_permission.id == setup_permission.id
    assert retrieved_permission.object == setup_permission.object
    assert retrieved_permission.action == setup_permission.action


def test_get_permissions(db, setup_permission):
    """Test retrieving a list of permissions."""
    # Get all permissions
    permissions = PermissionService(db).get_permissions()

    # Assertions
    assert len(permissions) >= 1
    assert any(p.id == setup_permission.id for p in permissions)


def test_get_permissions_with_pagination(
    db, setup_permission, setup_another_permission
):
    """Test retrieving permissions with pagination."""
    # Get permissions with limit
    permissions = PermissionService(db).get_permissions(skip=0, limit=1)

    # Assertions
    assert len(permissions) == 1

    # Get permissions with skip
    permissions = PermissionService(db).get_permissions(skip=1, limit=1)

    # Assertions
    assert len(permissions) <= 1


def test_update_permission(db, setup_permission, faker):
    """Test updating a permission."""
    # Update data
    update_data = {
        "object": faker.word().lower(),
        "action": faker.word().lower(),
    }
    permission_update = PermissionUpdate(**update_data)

    # Update permission
    updated_permission = PermissionService(db).update_permission(
        setup_permission.id, permission_update
    )

    # Assertions
    assert updated_permission is not None
    assert updated_permission.id == setup_permission.id
    assert updated_permission.object == update_data["object"]
    assert updated_permission.action == update_data["action"]
    # role_id should remain unchanged
    assert updated_permission.role_id == setup_permission.role_id


def test_update_permission_partial(db, setup_permission, faker):
    """Test updating a permission with partial data."""
    # Update only action
    update_data = {"action": faker.word().lower()}
    permission_update = PermissionUpdate(**update_data)

    # Update permission
    updated_permission = PermissionService(db).update_permission(
        setup_permission.id, permission_update
    )

    # Assertions
    assert updated_permission is not None
    assert updated_permission.id == setup_permission.id
    assert updated_permission.action == update_data["action"]
    # Object should remain unchanged
    assert updated_permission.object == setup_permission.object
    # role_id should remain unchanged
    assert updated_permission.role_id == setup_permission.role_id


def test_delete_permission(db, setup_permission):
    """Test deleting a permission."""
    permission_service = PermissionService(db)
    # Delete permission
    success = permission_service.delete_permission(setup_permission.id)

    # Assertions
    assert success is True
    deleted_permission = permission_service.get_permission(setup_permission.id)
    assert deleted_permission is None


def test_permission_not_found_cases(db, setup_role):
    """Test various not found cases."""
    permission_service = PermissionService(db)
    # Test various not found cases
    non_existent_id = uuid4()

    # Get non-existent permission
    assert permission_service.get_permission(non_existent_id) is None

    # Get by non-existent object and action
    assert (
        permission_service.get_permission_by_object_and_action(
            "nonexistent_object", "nonexistent_action", setup_role.id
        )
        is None
    )

    # Update non-existent permission
    update_data = {"action": "updated_action"}
    permission_update = PermissionUpdate(**update_data)
    assert (
        permission_service.update_permission(non_existent_id, permission_update) is None
    )

    # Delete non-existent permission
    assert permission_service.delete_permission(non_existent_id) is False


def test_search_permissions_with_filters(db, setup_permission):
    """Test searching permissions with dynamic filters."""
    # Search using ilike filter on object
    filters = {
        "object": {
            "operator": "ilike",
            "value": "%" + setup_permission.object[:3] + "%",
        }
    }
    results = PermissionService(db).search(filters)

    assert isinstance(results, list)
    assert any(permission.id == setup_permission.id for permission in results)

    # Search using exact match
    filters = {"object": setup_permission.object, "action": setup_permission.action}
    results = PermissionService(db).search(filters)

    assert len(results) >= 1
    assert any(p.id == setup_permission.id for p in results)

    # Search with no match
    filters = {"object": {"operator": "==", "value": "nonexistent_object"}}
    results = PermissionService(db).search(filters)

    assert len(results) == 0


def test_search_permissions_by_action(db, setup_permission):
    """Test searching permissions by action."""
    # Search using ilike filter on action
    filters = {
        "action": {
            "operator": "ilike",
            "value": "%" + setup_permission.action[:3] + "%",
        }
    }
    results = PermissionService(db).search(filters)

    assert isinstance(results, list)
    assert any(permission.id == setup_permission.id for permission in results)


def test_search_permissions_by_role_id(db, setup_permission):
    """Test searching permissions by role_id."""
    # Search using exact match on role_id
    filters = {"role_id": str(setup_permission.role_id)}
    results = PermissionService(db).search(filters)

    assert isinstance(results, list)
    assert any(permission.id == setup_permission.id for permission in results)
