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
            "identifier": faker.uuid4(),
        }
        response = client.post("/roles/", json=role_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == role_data["name"]
        assert data["description"] == role_data["description"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_role_duplicate_name(self, client, setup_role, faker):
        """Test creating a role with duplicate name."""
        role_data = {
            "name": setup_role.name,
            "description": "Duplicate role",
            "identifier": faker.uuid4(),
        }
        response = client.post("/roles/", json=role_data)
        assert response.status_code == 400
        data = response.json()
        assert "already exists" in data["detail"].lower()

    def test_create_role_without_description(self, client, faker):
        """Test creating a role without description."""
        role_data = {
            "name": faker.word().capitalize() + "Role",
            "identifier": faker.uuid4(),
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
        assert response.status_code == 404

    def test_update_role_invalid_uuid(self, client):
        """Test updating a role with invalid UUID format."""
        response = client.put("/roles/invalid-uuid", json={"name": "Test"})
        assert response.status_code == 404

    def test_delete_role_invalid_uuid(self, client):
        """Test deleting a role with invalid UUID format."""
        response = client.delete("/roles/invalid-uuid")
        assert response.status_code == 404

    def test_create_roles_batch_success(self, client, faker):
        """Test creating multiple roles with permissions in batch."""
        batch_data = [
            {
                "name": faker.word().capitalize() + "Collaborator",
                "description": "A collaborator role",
                "identifier": faker.uuid4(),
                "permissions": [
                    {"object": "contact", "action": "read"},
                    {"object": "contact", "action": "write"},
                ],
            },
            {
                "name": faker.word().capitalize() + "Owner",
                "description": "An owner role",
                "identifier": faker.uuid4(),
                "permissions": [
                    {"object": "workspace", "action": "manage"},
                ],
            },
        ]
        response = client.post("/roles/batch", json=batch_data)
        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

        # Verify first role
        role1 = data[0]
        assert role1["name"] == batch_data[0]["name"]
        assert role1["description"] == batch_data[0]["description"]
        assert "id" in role1
        assert "created_at" in role1

        # Verify second role
        role2 = data[1]
        assert role2["name"] == batch_data[1]["name"]
        assert role2["description"] == batch_data[1]["description"]
        assert "id" in role2

        # Verify permissions were created
        role1_id = role1["id"]
        perm_response = client.get(f"/roles/{role1_id}/permissions")
        assert perm_response.status_code == 200
        permissions = perm_response.json()
        assert len(permissions) == 2
        assert any(
            p["object"] == "contact" and p["action"] == "read" for p in permissions
        )
        assert any(
            p["object"] == "contact" and p["action"] == "write" for p in permissions
        )

    def test_create_roles_batch_duplicate_names_in_batch(self, client, faker):
        """Test creating batch with duplicate role names."""
        batch_data = [
            {
                "name": "DuplicateRole",
                "description": "First role",
                "identifier": faker.uuid4(),
                "permissions": [{"object": "test", "action": "read"}],
            },
            {
                "name": "DuplicateRole",
                "description": "Second role with same name",
                "identifier": faker.uuid4(),
                "permissions": [{"object": "test", "action": "write"}],
            },
        ]
        response = client.post("/roles/batch", json=batch_data)
        assert response.status_code == 400
        data = response.json()
        assert "duplicate" in data["detail"].lower()

    def test_create_roles_batch_empty_list(self, client):
        """Test creating batch with empty list."""
        response = client.post("/roles/batch", json=[])
        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_create_roles_batch_no_permissions(self, client, faker):
        """Test creating batch with roles that have no permissions."""
        batch_data = [
            {
                "name": faker.word().capitalize() + "Role",
                "identifier": faker.uuid4(),
                "description": "Role without permissions",
                "permissions": [],
            },
        ]
        response = client.post("/roles/batch", json=batch_data)
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == batch_data[0]["name"]

        # Verify no permissions were created
        role_id = data[0]["id"]
        perm_response = client.get(f"/roles/{role_id}/permissions")
        assert perm_response.status_code == 200
        permissions = perm_response.json()
        assert len(permissions) == 0

    def test_create_roles_batch_missing_required_fields(self, client):
        """Test creating batch with missing required fields."""
        batch_data = [
            {
                "description": "Role without name",
                "permissions": [],
            },
        ]
        response = client.post("/roles/batch", json=batch_data)
        assert response.status_code == 422  # Validation error

    def test_create_roles_batch_invalid_permission_format(self, client, faker):
        """Test creating batch with invalid permission format."""
        batch_data = [
            {
                "name": faker.word().capitalize() + "Role",
                "description": "Role with invalid permission",
                "identifier": faker.uuid4(),
                "permissions": [
                    {"object": "test"},  # Missing action
                ],
            },
        ]
        response = client.post("/roles/batch", json=batch_data)
        assert response.status_code == 422  # Validation error

    def test_create_roles_batch_large_batch(self, client, faker):
        """Test creating a large batch of roles."""
        batch_data = []
        for i in range(5):
            batch_data.append(
                {
                    "name": faker.word().capitalize() + f"Role{i}",
                    "description": f"Role {i}",
                    "identifier": faker.uuid4(),
                    "permissions": [
                        {"object": f"resource{i}", "action": "read"},
                        {"object": f"resource{i}", "action": "write"},
                    ],
                }
            )

        response = client.post("/roles/batch", json=batch_data)
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 5

        # Verify all roles were created
        for i, role in enumerate(data):
            assert role["name"] == batch_data[i]["name"]
            # Verify permissions
            perm_response = client.get(f"/roles/{role['id']}/permissions")
            assert perm_response.status_code == 200
            permissions = perm_response.json()
            assert len(permissions) == 2

    def test_bind_role_success(self, client, setup_role, db, faker):
        """Test successfully binding a role to a domain."""
        from app.models.permission import Permission

        # Create permissions for the role
        domain = faker.word().lower()
        permissions = [
            Permission(object="users", action="read", role_id=setup_role.id),
            Permission(object="users", action="write", role_id=setup_role.id),
            Permission(object="projects", action="read", role_id=setup_role.id),
        ]
        for perm in permissions:
            db.add(perm)
        db.commit()

        bind_data = {"domain": domain}
        response = client.post(f"/roles/{setup_role.id}/policies", json=bind_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["role_name"] == setup_role.name
        assert data["total_permissions"] == 3
        assert data["policies_added"] == 3
        assert data["policies_failed"] == 0

    def test_bind_role_not_found(self, client, faker):
        """Test binding a non-existent role."""
        non_existent_id = uuid4()
        bind_data = {"domain": faker.word().lower()}
        response = client.post(f"/roles/{non_existent_id}/policies", json=bind_data)
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_bind_role_no_permissions(self, client, setup_role, faker):
        """Test binding a role with no permissions."""
        domain = faker.word().lower()
        bind_data = {"domain": domain}
        response = client.post(f"/roles/{setup_role.id}/policies", json=bind_data)
        print(response.json())
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["role_name"] == setup_role.name
        assert data["total_permissions"] == 0
        assert data["policies_added"] == 0
        assert data["policies_failed"] == 0

    def test_bind_role_invalid_uuid(self, client, faker):
        """Test binding a role with invalid UUID format."""
        bind_data = {"domain": faker.word().lower()}
        response = client.post("/roles/invalid-uuid/policies", json=bind_data)
        assert response.status_code == 404

    def test_bind_role_missing_domain(self, client, setup_role):
        """Test binding a role without domain field."""
        bind_data = {}
        response = client.post(f"/roles/{setup_role.id}/policies", json=bind_data)
        assert response.status_code == 422
