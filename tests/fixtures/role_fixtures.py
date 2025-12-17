import pytest
from app.models.role import Role


@pytest.fixture(scope="function")
def setup_role(db, faker):
    """Create a test role for use in tests."""
    role_data = {
        "name": faker.word().capitalize() + "Role",
        "description": faker.text(100),
    }

    role = Role(**role_data)
    db.add(role)
    db.commit()
    db.refresh(role)

    return role


@pytest.fixture(scope="function")
def setup_another_role(db, faker):
    """Create another test role for use in tests."""
    role_data = {
        "name": faker.word().capitalize() + "Role",
        "description": faker.text(100),
    }

    role = Role(**role_data)
    db.add(role)
    db.commit()
    db.refresh(role)

    return role
