import pytest
from uuid import uuid4


class TestRoleRouter:
    """Test cases for the role CRUD endpoints."""

    def test_list_roles_empty(self, client):
        """Test listing roles when no roles exist."""
        response = client.get("/roles/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) == 0
        assert "total" in data
        assert data["total"] == 0

    def test_list_roles_with_data(self, client, setup_role):
        """Test listing roles when roles exist."""
        response = client.get("/roles/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) >= 1
        assert any(role["id"] == str(setup_role.id) for role in data["items"])
        assert "total" in data
        assert data["total"] >= 1

    def test_list_roles_with_pagination(self, client, setup_role, setup_another_role):
        """Test listing roles with pagination parameters."""
        response = client.get("/roles/?page=1&size=1")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert "page" in data
        assert "size" in data
        assert "pages" in data

        response = client.get("/roles/?page=2&size=1")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) <= 1

    def test_get_role_success(self, client, setup_role):
        """Test retrieving a role by ID."""
        response = client.get(f"/roles/{setup_role.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(setup_role.id)
        assert data["name"] == setup_role.name
        assert data["description"] == setup_role.description

    def test_get_role_not_found(self, client):
        """Test retrieving a non-existent role."""
        non_existent_id = uuid4()
        response = client.get(f"/roles/{non_existent_id}")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_create_role_success(self, client, faker):
        """Test creating a new role."""
        role_data = {
            "name": faker.word().capitalize() + "Role",
            "description": faker.text(100),
        }
        response = client.post("/roles/", json=role_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == role_data["name"]
        assert data["description"] == role_data["description"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_role_duplicate_name(self, client, setup_role):
        """Test creating a role with duplicate name."""
        role_data = {
            "name": setup_role.name,
            "description": "Duplicate role",
        }
        response = client.post("/roles/", json=role_data)
        assert response.status_code == 400
        data = response.json()
        assert "already exists" in data["detail"].lower()

    def test_create_role_without_description(self, client, faker):
        """Test creating a role without description."""
        role_data = {
            "name": faker.word().capitalize() + "Role",
        }
        response = client.post("/roles/", json=role_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == role_data["name"]
        assert data["description"] is None

    def test_update_role_success(self, client, setup_role, faker):
        """Test updating a role."""
        update_data = {
            "name": faker.word().capitalize() + "UpdatedRole",
            "description": faker.text(100),
        }
        response = client.put(f"/roles/{setup_role.id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(setup_role.id)
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]

    def test_update_role_partial(self, client, setup_role, faker):
        """Test partial update of a role."""
        original_description = setup_role.description
        update_data = {
            "name": faker.word().capitalize() + "PartialRole",
        }
        response = client.put(f"/roles/{setup_role.id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(setup_role.id)
        assert data["name"] == update_data["name"]
        # Description should remain unchanged if not provided
        assert data["description"] == original_description

    def test_update_role_not_found(self, client, faker):
        """Test updating a non-existent role."""
        non_existent_id = uuid4()
        update_data = {
            "name": faker.word().capitalize() + "Role",
        }
        response = client.put(f"/roles/{non_existent_id}", json=update_data)
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_update_role_duplicate_name(self, client, setup_role, setup_another_role):
        """Test updating a role with duplicate name."""
        update_data = {
            "name": setup_another_role.name,
        }
        response = client.put(f"/roles/{setup_role.id}", json=update_data)
        assert response.status_code == 400
        data = response.json()
        assert "already exists" in data["detail"].lower()

    def test_update_role_same_name(self, client, setup_role):
        """Test updating a role with the same name (should succeed)."""
        update_data = {
            "name": setup_role.name,
            "description": "Updated description",
        }
        response = client.put(f"/roles/{setup_role.id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == setup_role.name
        assert data["description"] == "Updated description"

    def test_delete_role_success(self, client, setup_role):
        """Test deleting a role."""
        role_id = setup_role.id
        response = client.delete(f"/roles/{role_id}")
        assert response.status_code == 204

        # Verify role is deleted
        get_response = client.get(f"/roles/{role_id}")
        assert get_response.status_code == 404

    def test_delete_role_not_found(self, client):
        """Test deleting a non-existent role."""
        non_existent_id = uuid4()
        response = client.delete(f"/roles/{non_existent_id}")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_create_role_missing_name(self, client):
        """Test creating a role without required name field."""
        role_data = {
            "description": "Role without name",
        }
        response = client.post("/roles/", json=role_data)
        assert response.status_code == 422  # Validation error

    def test_list_roles_invalid_pagination(self, client):
        """Test listing roles with invalid pagination parameters."""
        # Negative page
        response = client.get("/roles/?page=-1")
        assert response.status_code == 422

        # Zero size
        response = client.get("/roles/?size=0")
        assert response.status_code == 422

    def test_get_role_invalid_uuid(self, client):
        """Test retrieving a role with invalid UUID format."""
        response = client.get("/roles/invalid-uuid")
        assert response.status_code == 422

    def test_update_role_invalid_uuid(self, client):
        """Test updating a role with invalid UUID format."""
        response = client.put("/roles/invalid-uuid", json={"name": "Test"})
        assert response.status_code == 422

    def test_delete_role_invalid_uuid(self, client):
        """Test deleting a role with invalid UUID format."""
        response = client.delete("/roles/invalid-uuid")
        assert response.status_code == 422
