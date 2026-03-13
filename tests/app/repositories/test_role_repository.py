from uuid import uuid4
from app.schemas.role import RoleCreate, RoleUpdate
from app.repositories.role_repository import RoleRepository


def test_create_role(db, faker):
    """Test creating a new role."""
    # Create role
    role_data = {
        "name": faker.word().capitalize() + "Role",
        "identifier": faker.uuid4(),
        "description": faker.text(100),
    }
    role_create = RoleCreate(**role_data)
    role = RoleRepository(db).create_role(role_create)

    # Assertions
    assert role.id is not None
    assert role.name == role_data["name"]
    assert role.description == role_data["description"]
    assert role.created_at is not None
    assert role.updated_at is not None


def test_get_role(db, setup_role):
    """Test retrieving a role by ID."""
    # Get role
    retrieved_role = RoleRepository(db).get_role(setup_role.id)

    # Assertions
    assert retrieved_role is not None
    assert retrieved_role.id == setup_role.id
    assert retrieved_role.name == setup_role.name
    assert retrieved_role.description == setup_role.description


def test_get_role_by_name(db, setup_role):
    """Test retrieving a role by name."""
    # Get role by name
    retrieved_role = RoleRepository(db).get_role_by_name(setup_role.name)

    # Assertions
    assert retrieved_role is not None
    assert retrieved_role.id == setup_role.id
    assert retrieved_role.name == setup_role.name


def test_get_roles(db, setup_role):
    """Test retrieving a list of roles."""
    # Get all roles
    roles = RoleRepository(db).get_roles()

    # Assertions
    assert len(roles) >= 1
    assert any(r.id == setup_role.id for r in roles)


def test_get_roles_with_pagination(db, setup_role, setup_another_role):
    """Test retrieving roles with pagination."""
    # Get roles with limit
    roles = RoleRepository(db).get_roles(skip=0, limit=1)

    # Assertions
    assert len(roles) == 1

    # Get roles with skip
    roles = RoleRepository(db).get_roles(skip=1, limit=1)

    # Assertions
    assert len(roles) <= 1


def test_update_role(db, setup_role, faker):
    """Test updating a role."""
    # Update data
    update_data = {
        "name": faker.word().capitalize() + "UpdatedRole",
        "description": faker.text(100),
    }
    role_update = RoleUpdate(**update_data)

    # Update role
    updated_role = RoleRepository(db).update_role(setup_role.id, role_update)

    # Assertions
    assert updated_role is not None
    assert updated_role.id == setup_role.id
    assert updated_role.name == update_data["name"]
    assert updated_role.description == update_data["description"]


def test_update_role_partial(db, setup_role, faker):
    """Test updating a role with partial data."""
    # Update only name
    update_data = {"name": faker.word().capitalize() + "PartialRole"}
    role_update = RoleUpdate(**update_data)

    # Update role
    updated_role = RoleRepository(db).update_role(setup_role.id, role_update)

    # Assertions
    assert updated_role is not None
    assert updated_role.id == setup_role.id
    assert updated_role.name == update_data["name"]
    # Description should remain unchanged
    assert updated_role.description == setup_role.description


def test_delete_role(db, setup_role):
    """Test deleting a role."""
    role_repository = RoleRepository(db)
    # Delete role
    success = role_repository.delete_role(setup_role.id)

    # Assertions
    assert success is True
    deleted_role = role_repository.get_role(setup_role.id)
    assert deleted_role is None


def test_role_not_found_cases(db):
    """Test various not found cases."""
    role_repository = RoleRepository(db)
    # Test various not found cases
    non_existent_id = uuid4()

    # Get non-existent role
    assert role_repository.get_role(non_existent_id) is None

    # Get by non-existent name
    assert role_repository.get_role_by_name("nonexistent_role") is None

    # Update non-existent role
    update_data = {"name": "updated_role"}
    role_update = RoleUpdate(**update_data)
    assert role_repository.update_role(non_existent_id, role_update) is None

    # Delete non-existent role
    assert role_repository.delete_role(non_existent_id) is False


def test_search_roles_with_filters(db, setup_role):
    """Test searching roles with dynamic filters."""
    # Search using ilike filter on name
    filters = {"name": {"operator": "ilike", "value": "%" + setup_role.name[:5] + "%"}}
    results = RoleRepository(db).search(filters)

    assert isinstance(results, list)
    assert any(role.id == setup_role.id for role in results)

    # Search using exact match
    filters = {"name": setup_role.name}
    results = RoleRepository(db).search(filters)

    assert len(results) == 1
    assert results[0].id == setup_role.id

    # Search with no match
    filters = {"name": {"operator": "==", "value": "nonexistent_role"}}
    results = RoleRepository(db).search(filters)

    assert len(results) == 0


def test_search_roles_by_description(db, setup_role):
    """Test searching roles by description."""
    # Search using ilike filter on description
    if setup_role.description:
        filters = {
            "description": {
                "operator": "ilike",
                "value": "%" + setup_role.description[:10] + "%",
            }
        }
        results = RoleRepository(db).search(filters)

        assert isinstance(results, list)
        assert any(role.id == setup_role.id for role in results)
