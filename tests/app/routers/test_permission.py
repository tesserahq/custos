import pytest
from uuid import uuid4


class TestPermissionRouter:
    """Test cases for the permission endpoints."""

    def test_list_permissions_empty(self, client):
        """Test listing permissions returns correct structure."""
        response = client.get("/permissions/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert "total" in data
        assert isinstance(data["total"], int)
        assert "page" in data
        assert "size" in data
        assert "pages" in data

    def test_list_permissions_with_data(self, client, setup_permission):
        """Test listing permissions when permissions exist."""
        response = client.get("/permissions/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) >= 1
        assert "total" in data
        assert data["total"] >= 1

        # Verify the permission we created exists by fetching it directly
        # (it might be on a different page due to pagination)
        get_response = client.get(f"/permissions/{setup_permission.id}")
        assert get_response.status_code == 200
        permission_data = get_response.json()
        assert permission_data["id"] == str(setup_permission.id)
        assert permission_data["object"] == setup_permission.object
        assert permission_data["action"] == setup_permission.action

    def test_list_permissions_with_pagination(
        self, client, setup_permission, setup_another_permission
    ):
        """Test listing permissions with pagination parameters."""
        response = client.get("/permissions/?page=1&size=1")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert "page" in data
        assert "size" in data
        assert "pages" in data

        response = client.get("/permissions/?page=2&size=1")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) <= 1

    def test_list_permissions_invalid_pagination(self, client):
        """Test listing permissions with invalid pagination parameters."""
        # Negative page
        response = client.get("/permissions/?page=-1")
        assert response.status_code == 422

        # Zero size
        response = client.get("/permissions/?size=0")
        assert response.status_code == 422

    def test_get_permission_success(self, client, setup_permission):
        """Test retrieving a permission by ID."""
        response = client.get(f"/permissions/{setup_permission.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(setup_permission.id)
        assert data["object"] == setup_permission.object
        assert data["action"] == setup_permission.action
        assert data["role_id"] == str(setup_permission.role_id)

    def test_get_permission_not_found(self, client):
        """Test retrieving a non-existent permission."""
        non_existent_id = uuid4()
        response = client.get(f"/permissions/{non_existent_id}")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_permission_invalid_uuid(self, client):
        """Test retrieving a permission with invalid UUID format."""
        response = client.get("/permissions/invalid-uuid")
        assert response.status_code == 422

    def test_update_permission_success(self, client, setup_permission, faker):
        """Test updating a permission."""
        update_data = {
            "object": faker.word().lower(),
            "action": faker.word().lower(),
        }
        response = client.put(f"/permissions/{setup_permission.id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(setup_permission.id)
        assert data["object"] == update_data["object"]
        assert data["action"] == update_data["action"]

    def test_update_permission_partial(self, client, setup_permission, faker):
        """Test partial update of a permission."""
        original_action = setup_permission.action
        update_data = {
            "object": faker.word().lower(),
        }
        response = client.put(f"/permissions/{setup_permission.id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(setup_permission.id)
        assert data["object"] == update_data["object"]
        # Action should remain unchanged if not provided
        assert data["action"] == original_action

    def test_update_permission_not_found(self, client, faker):
        """Test updating a non-existent permission."""
        non_existent_id = uuid4()
        update_data = {
            "object": faker.word().lower(),
            "action": faker.word().lower(),
        }
        response = client.put(f"/permissions/{non_existent_id}", json=update_data)
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_update_permission_invalid_uuid(self, client):
        """Test updating a permission with invalid UUID format."""
        response = client.put("/permissions/invalid-uuid", json={"object": "test"})
        assert response.status_code == 422

    def test_delete_permission_success(self, client, setup_permission):
        """Test deleting a permission."""
        permission_id = setup_permission.id
        response = client.delete(f"/permissions/{permission_id}")
        assert response.status_code == 204

        # Verify permission is deleted
        get_response = client.get(f"/permissions/{permission_id}")
        assert get_response.status_code == 404

    def test_delete_permission_not_found(self, client):
        """Test deleting a non-existent permission."""
        non_existent_id = uuid4()
        response = client.delete(f"/permissions/{non_existent_id}")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_delete_permission_invalid_uuid(self, client):
        """Test deleting a permission with invalid UUID format."""
        response = client.delete("/permissions/invalid-uuid")
        assert response.status_code == 422


class TestRolePermissionRouter:
    """Test cases for the nested role-permission endpoints."""

    def test_list_role_permissions_empty(self, client, setup_role):
        """Test listing permissions for a role with no permissions."""
        response = client.get(f"/roles/{setup_role.id}/permissions")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) == 0
        assert "total" in data
        assert data["total"] == 0

    def test_list_role_permissions_with_data(
        self, client, setup_role, setup_permission
    ):
        """Test listing permissions for a role with permissions."""
        # Ensure the permission belongs to the role
        if setup_permission.role_id != setup_role.id:
            pytest.skip("Permission doesn't belong to the role")

        response = client.get(f"/roles/{setup_role.id}/permissions")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) >= 1
        assert any(perm["id"] == str(setup_permission.id) for perm in data["items"])
        assert "total" in data
        assert data["total"] >= 1

    def test_list_role_permissions_role_not_found(self, client):
        """Test listing permissions for a non-existent role."""
        non_existent_id = uuid4()
        response = client.get(f"/roles/{non_existent_id}/permissions")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_list_role_permissions_invalid_uuid(self, client):
        """Test listing permissions with invalid role UUID format."""
        response = client.get("/roles/invalid-uuid/permissions")
        assert response.status_code == 404

    def test_create_role_permission_success(self, client, setup_role, faker):
        """Test creating a permission for a role."""
        permission_data = {
            "object": faker.word().lower(),
            "action": faker.word().lower(),
        }
        response = client.post(
            f"/roles/{setup_role.id}/permissions", json=permission_data
        )
        assert response.status_code == 201
        data = response.json()
        assert data["object"] == permission_data["object"]
        assert data["action"] == permission_data["action"]
        assert data["role_id"] == str(setup_role.id)
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_role_permission_duplicate(self, client, setup_permission):
        """Test creating a duplicate permission for a role."""
        permission_data = {
            "object": setup_permission.object,
            "action": setup_permission.action,
        }
        response = client.post(
            f"/roles/{setup_permission.role_id}/permissions", json=permission_data
        )
        assert response.status_code == 400
        data = response.json()
        assert "already exists" in data["detail"].lower()

    def test_create_role_permission_role_not_found(self, client, faker):
        """Test creating a permission for a non-existent role."""
        non_existent_id = uuid4()
        permission_data = {
            "object": faker.word().lower(),
            "action": faker.word().lower(),
        }
        response = client.post(
            f"/roles/{non_existent_id}/permissions", json=permission_data
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_create_role_permission_missing_fields(self, client, setup_role):
        """Test creating a permission without required fields."""
        # Missing object
        response = client.post(
            f"/roles/{setup_role.id}/permissions", json={"action": "read"}
        )
        assert response.status_code == 422

        # Missing action
        response = client.post(
            f"/roles/{setup_role.id}/permissions", json={"object": "users"}
        )
        assert response.status_code == 422

    def test_create_role_permission_invalid_uuid(self, client):
        """Test creating a permission with invalid role UUID format."""
        response = client.post(
            "/roles/invalid-uuid/permissions", json={"object": "test", "action": "read"}
        )
        assert response.status_code == 404
