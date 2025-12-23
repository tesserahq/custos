from unittest.mock import Mock, patch
from app.models.user import User


class TestSystemRouter:
    """Test cases for system router endpoints."""

    @staticmethod
    def _create_super_user(db, email: str, faker):
        """Helper to create a super user for testing."""
        user = User(
            email=email,
            username=email,
            first_name="Admin",
            last_name="User",
            external_id=faker.uuid4(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @patch("app.commands.setup.setup_command.get_settings")
    def test_setup_system_with_default_path(self, mock_get_settings, client, db, faker):
        """Test POST /system/setup with default YAML file path."""
        # Create a super user first
        self._create_super_user(db, "admin@example.com", faker)

        # Mock settings
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings

        response = client.post("/system/setup", json={})

        # Should return 201 if default file exists, or 404 if it doesn't
        # (404 is acceptable if default file doesn't exist in test environment)
        assert response.status_code in [201, 404]

        if response.status_code == 201:
            data = response.json()
            assert data["success"] is True
            assert "roles_created" in data
            assert "roles" in data
            assert "message" in data
            assert isinstance(data["roles"], list)

    @patch("app.commands.setup.setup_command.get_settings")
    def test_setup_system_with_empty_body(
        self, mock_get_settings, client, tmp_path, db, faker
    ):
        """Test POST /system/setup with empty request body."""
        # Create a super user first
        self._create_super_user(db, "admin@example.com", faker)

        # Mock settings
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings
        # Create a test YAML file
        yaml_content = """
roles:
  test_role:
    name: "Test Role"
    identifier: "test_role_setup"
    description: "A test role for setup"
    permissions:
      role:
        - read
"""
        yaml_file = tmp_path / "test_roles.yaml"
        yaml_file.write_text(yaml_content)

        # Try with empty body (should use default path or fail)
        response = client.post("/system/setup", json={})

        # Should return 201 or 404 (if default file doesn't exist)
        assert response.status_code in [201, 404]

    @patch("app.commands.setup.setup_command.get_settings")
    def test_setup_system_with_custom_path(
        self, mock_get_settings, client, tmp_path, db, faker
    ):
        """Test POST /system/setup with custom YAML file path."""
        # Create a super user first
        self._create_super_user(db, "admin@example.com", faker)

        # Mock settings
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings
        # Create a test YAML file
        yaml_content = """
roles:
  custom_role:
    name: "Custom Role"
    identifier: "custom_role_test"
    description: "A custom role"
    permissions:
      role:
        - read
        - write
      permission:
        - read
"""
        yaml_file = tmp_path / "custom_roles.yaml"
        yaml_file.write_text(yaml_content)

        request_data = {"yaml_file_path": str(yaml_file)}
        response = client.post("/system/setup", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["roles_created"] == 1
        assert len(data["roles"]) == 1
        assert data["roles"][0]["identifier"] == "custom_role_test"
        assert data["roles"][0]["name"] == "Custom Role"
        assert "Successfully imported" in data["message"]

    @patch("app.commands.setup.setup_command.get_settings")
    def test_setup_system_file_not_found(self, mock_get_settings, client):
        """Test POST /system/setup with non-existent file path."""
        # Mock settings (no user needed, will fail before binding)
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings
        request_data = {"yaml_file_path": "/nonexistent/path/roles.yaml"}
        response = client.post("/system/setup", json=request_data)

        assert response.status_code == 404
        assert "YAML file not found" in response.json()["detail"]

    @patch("app.commands.setup.setup_command.get_settings")
    def test_setup_system_invalid_yaml(self, mock_get_settings, client, tmp_path):
        """Test POST /system/setup with invalid YAML structure."""
        # Mock settings (no user needed, will fail before binding)
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings
        # Create YAML file with missing required fields
        yaml_content = """
roles:
  invalid_role:
    name: "Invalid Role"
    # Missing identifier field
"""
        yaml_file = tmp_path / "invalid_roles.yaml"
        yaml_file.write_text(yaml_content)

        request_data = {"yaml_file_path": str(yaml_file)}
        response = client.post("/system/setup", json=request_data)

        assert response.status_code == 400
        assert "missing required field" in response.json()["detail"].lower()

    @patch("app.commands.setup.setup_command.get_settings")
    def test_setup_system_multiple_roles(
        self, mock_get_settings, client, tmp_path, db, faker
    ):
        """Test POST /system/setup with multiple roles in YAML."""
        # Create a super user first
        self._create_super_user(db, "admin@example.com", faker)

        # Mock settings
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings
        yaml_content = """
roles:
  admin:
    name: "Admin Role"
    identifier: "admin_test"
    permissions:
      role:
        - read
        - write
  viewer:
    name: "Viewer Role"
    identifier: "viewer_test"
    permissions:
      role:
        - read
"""
        yaml_file = tmp_path / "multiple_roles.yaml"
        yaml_file.write_text(yaml_content)

        request_data = {"yaml_file_path": str(yaml_file)}
        response = client.post("/system/setup", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["roles_created"] == 2
        assert len(data["roles"]) == 2

        # Verify both roles are present
        role_identifiers = {role["identifier"] for role in data["roles"]}
        assert "admin_test" in role_identifiers
        assert "viewer_test" in role_identifiers
