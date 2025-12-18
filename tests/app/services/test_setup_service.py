import pytest
import os
from unittest.mock import Mock, patch
from app.services.setup_service import SetupService
from app.services.permission_service import PermissionService
from app.models.user import User


class TestSetupService:
    """Test cases for SetupService."""

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
    def test_import_roles_from_yaml_success(
        self, mock_get_settings, db, tmp_path, faker
    ):
        """Test successfully importing roles from a YAML file."""
        # Create a super user first
        self._create_super_user(db, "admin@example.com", faker)

        # Mock settings with super_user_email
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings

        # Create a temporary YAML file
        yaml_content = """
roles:
  test_role:
    name: "Test Role"
    identifier: "test_role"
    description: "A test role"
    permissions:
      role:
        - read
        - write
      permission:
        - read
"""
        yaml_file = tmp_path / "test_roles.yaml"
        yaml_file.write_text(yaml_content)

        service = SetupService(db, nats_publisher=None)
        created_roles = service.import_roles_from_yaml(str(yaml_file))

        # Assertions
        assert len(created_roles) == 1
        assert created_roles[0].name == "Test Role"
        assert created_roles[0].identifier == "test_role"
        assert created_roles[0].description == "A test role"

        # Verify permissions were created
        permission_service = PermissionService(db)
        permissions = permission_service.get_permissions_by_role(created_roles[0].id)
        assert len(permissions) == 3  # role:read, role:write, permission:read

        # Verify specific permissions
        permission_objects = {(p.object, p.action) for p in permissions}
        assert ("role", "read") in permission_objects
        assert ("role", "write") in permission_objects
        assert ("permission", "read") in permission_objects

    @patch("app.commands.setup.setup_command.get_settings")
    def test_import_roles_from_yaml_default_path(self, mock_get_settings, db, faker):
        """Test importing roles using default YAML file path."""
        # Create a super user first
        self._create_super_user(db, "admin@example.com", faker)

        # Mock settings with super_user_email
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings

        # This test uses the actual default_roles.yaml file
        service = SetupService(db, nats_publisher=None)

        # Only run if the default file exists
        default_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "app",
            "config",
            "default_roles.yaml",
        )
        default_path = os.path.abspath(default_path)

        if os.path.exists(default_path):
            created_roles = service.import_roles_from_yaml()
            assert len(created_roles) > 0
            # Verify the role from default_roles.yaml
            assert any(r.identifier == "rbac_admin" for r in created_roles)

    @patch("app.commands.setup.setup_command.get_settings")
    def test_import_roles_from_yaml_multiple_roles(
        self, mock_get_settings, db, tmp_path, faker
    ):
        # Create a super user first
        self._create_super_user(db, "admin@example.com", faker)

        # Mock settings with super_user_email
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings
        """Test importing multiple roles from YAML file."""
        yaml_content = """
roles:
  admin:
    name: "Admin Role"
    identifier: "admin"
    description: "Administrator role"
    permissions:
      role:
        - read
        - write
  viewer:
    name: "Viewer Role"
    identifier: "viewer"
    description: "Viewer role"
    permissions:
      role:
        - read
"""
        yaml_file = tmp_path / "test_roles.yaml"
        yaml_file.write_text(yaml_content)

        service = SetupService(db, nats_publisher=None)
        created_roles = service.import_roles_from_yaml(str(yaml_file))

        # Assertions
        assert len(created_roles) == 2

        # Verify both roles exist
        role_identifiers = {r.identifier for r in created_roles}
        assert "admin" in role_identifiers
        assert "viewer" in role_identifiers

        # Verify role with more permissions
        admin_role = next(r for r in created_roles if r.identifier == "admin")
        admin_permissions = PermissionService(db).get_permissions_by_role(admin_role.id)
        assert len(admin_permissions) == 2

        # Verify viewer role with fewer permissions
        viewer_role = next(r for r in created_roles if r.identifier == "viewer")
        viewer_permissions = PermissionService(db).get_permissions_by_role(
            viewer_role.id
        )
        assert len(viewer_permissions) == 1

    @patch("app.commands.setup.setup_command.get_settings")
    def test_import_roles_from_yaml_file_not_found(self, mock_get_settings, db):
        # Mock settings with super_user_email
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings
        """Test that FileNotFoundError is raised when YAML file doesn't exist."""
        service = SetupService(db, nats_publisher=None)

        with pytest.raises(FileNotFoundError) as exc_info:
            service.import_roles_from_yaml("/nonexistent/path/roles.yaml")

        assert "YAML file not found" in str(exc_info.value)

    @patch("app.commands.setup.setup_command.get_settings")
    def test_import_roles_from_yaml_missing_roles_key(
        self, mock_get_settings, db, tmp_path
    ):
        # Mock settings with super_user_email
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings
        """Test that ValueError is raised when YAML file is missing 'roles' key."""
        yaml_content = """
some_other_key:
  data: "value"
"""
        yaml_file = tmp_path / "test_roles.yaml"
        yaml_file.write_text(yaml_content)

        service = SetupService(db, nats_publisher=None)

        with pytest.raises(ValueError) as exc_info:
            service.import_roles_from_yaml(str(yaml_file))

        assert "must contain a 'roles' key" in str(exc_info.value)

    @patch("app.commands.setup.setup_command.get_settings")
    def test_import_roles_from_yaml_missing_name(self, mock_get_settings, db, tmp_path):
        # Mock settings with super_user_email
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings
        """Test that ValueError is raised when role is missing 'name' field."""
        yaml_content = """
roles:
  test_role:
    identifier: "test_role"
    description: "A test role"
"""
        yaml_file = tmp_path / "test_roles.yaml"
        yaml_file.write_text(yaml_content)

        service = SetupService(db, nats_publisher=None)

        with pytest.raises(ValueError) as exc_info:
            service.import_roles_from_yaml(str(yaml_file))

        assert "missing required field 'name'" in str(exc_info.value)

    @patch("app.commands.setup.setup_command.get_settings")
    def test_import_roles_from_yaml_missing_identifier(
        self, mock_get_settings, db, tmp_path
    ):
        # Mock settings with super_user_email
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings
        """Test that ValueError is raised when role is missing 'identifier' field."""
        yaml_content = """
roles:
  test_role:
    name: "Test Role"
    description: "A test role"
"""
        yaml_file = tmp_path / "test_roles.yaml"
        yaml_file.write_text(yaml_content)

        service = SetupService(db, nats_publisher=None)

        with pytest.raises(ValueError) as exc_info:
            service.import_roles_from_yaml(str(yaml_file))

        assert "missing required field 'identifier'" in str(exc_info.value)

    @patch("app.commands.setup.setup_command.get_settings")
    def test_import_roles_from_yaml_permissions_not_list(
        self, mock_get_settings, db, tmp_path
    ):
        # Mock settings with super_user_email
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings
        """Test that ValueError is raised when permissions actions are not a list."""
        yaml_content = """
roles:
  test_role:
    name: "Test Role"
    identifier: "test_role"
    permissions:
      role: "not_a_list"
"""
        yaml_file = tmp_path / "test_roles.yaml"
        yaml_file.write_text(yaml_content)

        service = SetupService(db, nats_publisher=None)

        with pytest.raises(ValueError) as exc_info:
            service.import_roles_from_yaml(str(yaml_file))

        assert "must be a list of actions" in str(exc_info.value)

    @patch("app.commands.setup.setup_command.get_settings")
    def test_import_roles_from_yaml_without_description(
        self, mock_get_settings, db, tmp_path, faker
    ):
        # Create a super user first
        self._create_super_user(db, "admin@example.com", faker)

        # Mock settings with super_user_email
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings
        """Test importing role without description field."""
        yaml_content = """
roles:
  test_role:
    name: "Test Role"
    identifier: "test_role"
    permissions:
      role:
        - read
"""
        yaml_file = tmp_path / "test_roles.yaml"
        yaml_file.write_text(yaml_content)

        service = SetupService(db, nats_publisher=None)
        created_roles = service.import_roles_from_yaml(str(yaml_file))

        # Assertions
        assert len(created_roles) == 1
        assert created_roles[0].description is None

    @patch("app.commands.setup.setup_command.get_settings")
    def test_import_roles_from_yaml_without_permissions(
        self, mock_get_settings, db, tmp_path, faker
    ):
        # Create a super user first
        self._create_super_user(db, "admin@example.com", faker)

        # Mock settings with super_user_email
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings
        """Test importing role without permissions field."""
        yaml_content = """
roles:
  test_role:
    name: "Test Role"
    identifier: "test_role"
    description: "A test role"
"""
        yaml_file = tmp_path / "test_roles.yaml"
        yaml_file.write_text(yaml_content)

        service = SetupService(db, nats_publisher=None)
        created_roles = service.import_roles_from_yaml(str(yaml_file))

        # Assertions
        assert len(created_roles) == 1
        assert created_roles[0].name == "Test Role"

        # Verify no permissions were created
        permission_service = PermissionService(db)
        permissions = permission_service.get_permissions_by_role(created_roles[0].id)
        assert len(permissions) == 0

    @patch("app.commands.setup.setup_command.get_settings")
    def test_import_roles_from_yaml_duplicate_identifier(
        self, mock_get_settings, db, tmp_path, setup_role
    ):
        # Mock settings with super_user_email
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings
        """Test that ValueError is raised when role identifier already exists."""
        yaml_content = f"""
roles:
  existing_role:
    name: "Existing Role"
    identifier: "{setup_role.identifier}"
    description: "This should fail"
"""
        yaml_file = tmp_path / "test_roles.yaml"
        yaml_file.write_text(yaml_content)

        service = SetupService(db, nats_publisher=None)

        with pytest.raises(ValueError) as exc_info:
            service.import_roles_from_yaml(str(yaml_file))

        assert "already exists" in str(exc_info.value).lower()

    @patch("app.commands.setup.setup_command.get_settings")
    def test_import_roles_from_yaml_publishes_events(
        self, mock_get_settings, db, tmp_path, faker
    ):
        # Create a super user first
        self._create_super_user(db, "admin@example.com", faker)

        # Mock settings with super_user_email
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings
        """Test that events are published when nats_publisher is provided."""
        yaml_content = """
roles:
  test_role:
    name: "Test Role"
    identifier: "test_role"
    permissions:
      role:
        - read
"""
        yaml_file = tmp_path / "test_roles.yaml"
        yaml_file.write_text(yaml_content)

        # Mock the nats_publisher
        mock_publisher = Mock()
        mock_publisher.publish_sync = Mock()

        service = SetupService(db, nats_publisher=mock_publisher)
        service.import_roles_from_yaml(str(yaml_file))

        # Verify event was published (called through CreateRolesBatchCommand)
        assert mock_publisher.publish_sync.called

    @patch("app.commands.setup.setup_command.get_settings")
    def test_import_roles_from_yaml_transforms_permissions_correctly(
        self, mock_get_settings, db, tmp_path, faker
    ):
        # Create a super user first
        self._create_super_user(db, "admin@example.com", faker)

        # Mock settings with super_user_email
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings
        """Test that nested YAML permissions are correctly transformed to flat list."""
        yaml_content = """
roles:
  test_role:
    name: "Test Role"
    identifier: "test_role"
    permissions:
      role:
        - read
        - write
        - delete
      permission:
        - read
        - create
      user:
        - read
"""
        yaml_file = tmp_path / "test_roles.yaml"
        yaml_file.write_text(yaml_content)

        service = SetupService(db, nats_publisher=None)
        created_roles = service.import_roles_from_yaml(str(yaml_file))

        # Verify all permissions were created
        permission_service = PermissionService(db)
        permissions = permission_service.get_permissions_by_role(created_roles[0].id)

        # Should have 6 permissions total: 3 for role, 2 for permission, 1 for user
        assert len(permissions) == 6

        # Verify all expected permission combinations exist
        permission_set = {(p.object, p.action) for p in permissions}
        expected_permissions = {
            ("role", "read"),
            ("role", "write"),
            ("role", "delete"),
            ("permission", "read"),
            ("permission", "create"),
            ("user", "read"),
        }
        assert permission_set == expected_permissions

    @patch("app.commands.setup.setup_command.get_settings")
    def test_import_roles_from_yaml_empty_roles_dict(
        self, mock_get_settings, db, tmp_path, faker
    ):
        # Create a super user first (even though no roles will be created)
        self._create_super_user(db, "admin@example.com", faker)

        # Mock settings with super_user_email
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings
        """Test importing from YAML file with empty roles dictionary."""
        yaml_content = """
roles: {}
"""
        yaml_file = tmp_path / "test_roles.yaml"
        yaml_file.write_text(yaml_content)

        service = SetupService(db, nats_publisher=None)
        created_roles = service.import_roles_from_yaml(str(yaml_file))

        # Should return empty list
        assert len(created_roles) == 0

    @patch("app.commands.setup.setup_command.get_settings")
    def test_import_roles_from_yaml_invalid_yaml_syntax(
        self, mock_get_settings, db, tmp_path
    ):
        """Test that invalid YAML syntax raises appropriate error."""
        # Mock settings with super_user_email
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = ["admin@example.com"]
        mock_get_settings.return_value = mock_settings
        invalid_yaml = """
roles:
  test_role:
    name: "Test Role"
    identifier: "test_role"
    permissions:
      role: [read write  # Missing closing bracket
"""
        yaml_file = tmp_path / "test_roles.yaml"
        yaml_file.write_text(invalid_yaml)

        service = SetupService(db, nats_publisher=None)

        # Should raise a YAML parsing error (which may be wrapped)
        with pytest.raises(Exception) as exc_info:
            service.import_roles_from_yaml(str(yaml_file))

        # YAML parser will raise an exception for invalid syntax
        assert exc_info.value is not None

    def test_import_roles_from_yaml_missing_super_user_email(self, db, tmp_path):
        """Test that ValueError is raised when SUPER_USER_EMAIL is not configured."""
        yaml_content = """
roles:
  test_role:
    name: "Test Role"
    identifier: "test_role"
    permissions:
      role:
        - read
"""
        yaml_file = tmp_path / "test_roles.yaml"
        yaml_file.write_text(yaml_content)

        service = SetupService(db, nats_publisher=None)

        with patch(
            "app.commands.setup.setup_command.get_settings"
        ) as mock_get_settings:
            # Mock settings without super_user_email
            mock_settings = Mock()
            mock_settings.get_super_user_emails.return_value = []
            mock_get_settings.return_value = mock_settings

            with pytest.raises(ValueError) as exc_info:
                service.import_roles_from_yaml(str(yaml_file))

            assert "SUPER_USER_EMAIL" in str(exc_info.value)
            assert (
                "requires" in str(exc_info.value).lower()
                or "required" in str(exc_info.value).lower()
            )

    @patch("app.commands.setup.setup_command.get_settings")
    def test_import_roles_from_yaml_super_user_email_comma_separated(
        self, mock_get_settings, db, tmp_path, faker
    ):
        """Test that setup works with comma-separated super_user_email."""
        # Create super users first
        self._create_super_user(db, "admin1@example.com", faker)
        self._create_super_user(db, "admin2@example.com", faker)

        # Mock settings with multiple emails (comma-separated)
        mock_settings = Mock()
        mock_settings.get_super_user_emails.return_value = [
            "admin1@example.com",
            "admin2@example.com",
        ]
        mock_get_settings.return_value = mock_settings

        yaml_content = """
roles:
  test_role:
    name: "Test Role"
    identifier: "test_role_comma"
    permissions:
      role:
        - read
"""
        yaml_file = tmp_path / "test_roles.yaml"
        yaml_file.write_text(yaml_content)

        service = SetupService(db, nats_publisher=None)
        created_roles = service.import_roles_from_yaml(str(yaml_file))

        # Should succeed with multiple emails
        assert len(created_roles) == 1
        assert created_roles[0].identifier == "test_role_comma"
