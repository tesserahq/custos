import pytest
from app.models.permission import Permission


@pytest.fixture(scope="function")
def setup_permission(db, setup_role, faker):
    """Create a test permission for use in tests."""
    permission_data = {
        "object": faker.word().lower(),
        "action": faker.word().lower(),
        "role_id": setup_role.id,
    }

    permission = Permission(**permission_data)
    db.add(permission)
    db.commit()
    db.refresh(permission)

    return permission


@pytest.fixture(scope="function")
def setup_another_permission(db, setup_role, faker):
    """Create another test permission for use in tests."""
    permission_data = {
        "object": faker.word().lower(),
        "action": faker.word().lower(),
        "role_id": setup_role.id,
    }

    permission = Permission(**permission_data)
    db.add(permission)
    db.commit()
    db.refresh(permission)

    return permission
