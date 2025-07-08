"""
Tests for the Role Template Service
"""

import pytest
import tempfile
import os
import yaml
from unittest.mock import patch, MagicMock
from app.services.role_template_service import (
    RoleTemplateService,
    role_template_service,
)
from app.services.role_definition_service import role_definition_service


class TestRoleTemplateService:
    """Test cases for role template service functionality."""

    @pytest.fixture
    def temp_templates_dir(self):
        """Create a temporary templates directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Patch the templates directory
            with patch.object(role_template_service, "templates_dir", temp_dir):
                yield temp_dir

    @pytest.fixture
    def sample_role_config(self):
        """Sample role configuration for testing."""
        return {
            "roles": {
                "admin": {
                    "description": "Full system administrator",
                    "permissions": {
                        "users": ["read", "write", "delete", "create"],
                        "documents": ["read", "write", "delete", "create"],
                    },
                },
                "editor": {
                    "description": "Content editor",
                    "permissions": {
                        "users": ["read"],
                        "documents": ["read", "write", "create"],
                    },
                },
            }
        }

    def test_create_role_template(self, temp_templates_dir, sample_role_config):
        """Test creating a role template."""
        template_name = "test-template"

        success = role_template_service.create_role_template(
            template_name, sample_role_config
        )

        assert success is True

        # Verify template file was created
        template_file = os.path.join(temp_templates_dir, f"{template_name}.yaml")
        assert os.path.exists(template_file)

        # Verify content is correct
        with open(template_file, "r") as f:
            loaded_config = yaml.safe_load(f)

        assert loaded_config == sample_role_config

    def test_create_role_template_invalid_config(self, temp_templates_dir):
        """Test creating a template with invalid configuration."""
        template_name = "test-template"
        invalid_config = None

        # Mock yaml.dump to raise an exception
        with patch("yaml.dump") as mock_yaml_dump:
            mock_yaml_dump.side_effect = Exception("YAML dump failed")

            success = role_template_service.create_role_template(
                template_name, invalid_config
            )

            assert success is False

    def test_get_role_template(self, temp_templates_dir, sample_role_config):
        """Test getting a role template."""
        template_name = "test-template"

        # Create template first
        role_template_service.create_role_template(template_name, sample_role_config)

        # Get template
        config = role_template_service.get_role_template(template_name)

        assert config is not None
        assert config == sample_role_config

    def test_get_role_template_not_found(self, temp_templates_dir):
        """Test getting a non-existent template."""
        template_name = "non-existent-template"

        config = role_template_service.get_role_template(template_name)

        assert config is None

    def test_list_role_templates(self, temp_templates_dir, sample_role_config):
        """Test listing role templates."""
        # Create multiple templates
        role_template_service.create_role_template("template-1", sample_role_config)
        role_template_service.create_role_template("template-2", sample_role_config)

        templates = role_template_service.list_role_templates()

        assert "template-1" in templates
        assert "template-2" in templates
        assert len(templates) == 2

    def test_list_role_templates_empty_directory(self, temp_templates_dir):
        """Test listing templates when directory is empty."""
        templates = role_template_service.list_role_templates()

        assert templates == []

    @patch.object(role_definition_service, "get_role_permissions")
    @patch.object(role_template_service, "_define_role_from_config")
    def test_apply_template_to_domain(
        self,
        mock_define_role,
        mock_get_permissions,
        temp_templates_dir,
        sample_role_config,
    ):
        """Test applying a template to a domain."""
        template_name = "test-template"
        domain = "test-domain"

        # Create template
        role_template_service.create_role_template(template_name, sample_role_config)

        # Mock existing permissions check
        mock_get_permissions.return_value = []
        mock_define_role.return_value = True

        results = role_template_service.apply_template_to_domain(template_name, domain)

        # Verify results
        assert "admin" in results
        assert "editor" in results
        assert results["admin"] is True
        assert results["editor"] is True

        # Verify service calls
        assert mock_define_role.call_count == 2  # Called for admin and editor roles

    def test_apply_template_to_domain_template_not_found(self, temp_templates_dir):
        """Test applying a non-existent template."""
        template_name = "non-existent-template"
        domain = "test-domain"

        results = role_template_service.apply_template_to_domain(template_name, domain)

        assert "error" in results
        assert "not found" in results["error"]

    @patch.object(role_definition_service, "get_role_permissions")
    @patch.object(role_template_service, "_define_role_from_config")
    def test_apply_template_to_domain_with_existing_roles(
        self,
        mock_define_role,
        mock_get_permissions,
        temp_templates_dir,
        sample_role_config,
    ):
        """Test applying template when roles already exist."""
        template_name = "test-template"
        domain = "test-domain"

        # Create template
        role_template_service.create_role_template(template_name, sample_role_config)

        # Mock existing permissions for admin role
        def mock_get_permissions_side_effect(role_name, domain):
            if role_name == "admin":
                return [("users", "read")]  # Existing permissions
            return []

        mock_get_permissions.side_effect = mock_get_permissions_side_effect
        mock_define_role.return_value = True

        # Apply without overwriting
        results = role_template_service.apply_template_to_domain(
            template_name, domain, overwrite_existing=False
        )

        # Admin role should be skipped, editor should be created
        assert results["admin"] is False  # Skipped due to existing role
        assert results["editor"] is True  # Created successfully

    def test_apply_template_to_multiple_domains(
        self, temp_templates_dir, sample_role_config
    ):
        """Test applying template to multiple domains."""
        template_name = "test-template"
        domains = ["domain-1", "domain-2", "domain-3"]

        # Create template
        role_template_service.create_role_template(template_name, sample_role_config)

        # Mock the apply_template_to_domain method
        with patch.object(
            role_template_service, "apply_template_to_domain"
        ) as mock_apply:
            mock_apply.return_value = {"admin": True, "editor": True}

            results = role_template_service.apply_template_to_multiple_domains(
                template_name, domains
            )

            # Verify results structure
            assert len(results) == 3
            for domain in domains:
                assert domain in results
                assert results[domain] == {"admin": True, "editor": True}

            # Verify apply was called for each domain
            assert mock_apply.call_count == 3

    def test_update_template_and_apply(self, temp_templates_dir, sample_role_config):
        """Test updating template and applying to domains."""
        template_name = "test-template"
        domains = ["domain-1", "domain-2"]
        updated_config = {
            "roles": {
                "admin": {
                    "permissions": {
                        "users": ["read", "write", "delete", "create"],
                        "reports": ["read", "write"],  # New resource
                    }
                }
            }
        }

        # Create initial template
        role_template_service.create_role_template(template_name, sample_role_config)

        # Mock the apply_template_to_multiple_domains method
        with patch.object(
            role_template_service, "apply_template_to_multiple_domains"
        ) as mock_apply:
            mock_apply.return_value = {
                "domain-1": {"admin": True},
                "domain-2": {"admin": True},
            }

            results = role_template_service.update_template_and_apply(
                template_name, updated_config, domains
            )

            # Verify template was updated
            loaded_config = role_template_service.get_role_template(template_name)
            assert loaded_config == updated_config

            # Verify apply was called
            mock_apply.assert_called_once_with(template_name, domains, True)

    def test_add_permission_to_template(self, temp_templates_dir, sample_role_config):
        """Test adding permission to a role in template."""
        template_name = "test-template"

        # Create template
        role_template_service.create_role_template(template_name, sample_role_config)

        # Add permission
        success = role_template_service.add_permission_to_template(
            template_name, "admin", "reports", "read"
        )

        assert success is True

        # Verify permission was added
        updated_config = role_template_service.get_role_template(template_name)
        assert "reports" in updated_config["roles"]["admin"]["permissions"]
        assert "read" in updated_config["roles"]["admin"]["permissions"]["reports"]

    def test_add_permission_to_template_role_not_exists(
        self, temp_templates_dir, sample_role_config
    ):
        """Test adding permission to non-existent role."""
        template_name = "test-template"

        # Create template
        role_template_service.create_role_template(template_name, sample_role_config)

        # Add permission to non-existent role
        success = role_template_service.add_permission_to_template(
            template_name, "non-existent-role", "reports", "read"
        )

        assert success is True

        # Verify role was created with permission
        updated_config = role_template_service.get_role_template(template_name)
        assert "non-existent-role" in updated_config["roles"]
        assert "reports" in updated_config["roles"]["non-existent-role"]["permissions"]
        assert (
            "read"
            in updated_config["roles"]["non-existent-role"]["permissions"]["reports"]
        )

    def test_add_permission_to_template_duplicate_permission(
        self, temp_templates_dir, sample_role_config
    ):
        """Test adding duplicate permission."""
        template_name = "test-template"

        # Create template
        role_template_service.create_role_template(template_name, sample_role_config)

        # Add permission that already exists
        success = role_template_service.add_permission_to_template(
            template_name, "admin", "users", "read"
        )

        assert success is True

        # Verify permission still exists (not duplicated)
        updated_config = role_template_service.get_role_template(template_name)
        permissions = updated_config["roles"]["admin"]["permissions"]["users"]
        assert permissions.count("read") == 1  # Should not be duplicated

    def test_remove_permission_from_template(
        self, temp_templates_dir, sample_role_config
    ):
        """Test removing permission from a role in template."""
        template_name = "test-template"

        # Create template
        role_template_service.create_role_template(template_name, sample_role_config)

        # Remove permission
        success = role_template_service.remove_permission_from_template(
            template_name, "admin", "users", "read"
        )

        assert success is True

        # Verify permission was removed
        updated_config = role_template_service.get_role_template(template_name)
        assert "read" not in updated_config["roles"]["admin"]["permissions"]["users"]

    def test_remove_permission_from_template_not_exists(
        self, temp_templates_dir, sample_role_config
    ):
        """Test removing non-existent permission."""
        template_name = "test-template"

        # Create template
        role_template_service.create_role_template(template_name, sample_role_config)

        # Remove non-existent permission
        success = role_template_service.remove_permission_from_template(
            template_name, "admin", "users", "non-existent-action"
        )

        assert success is True

        # Verify template is unchanged
        updated_config = role_template_service.get_role_template(template_name)
        assert updated_config == sample_role_config

    def test_remove_permission_from_template_removes_empty_resource(
        self, temp_templates_dir
    ):
        """Test that removing last permission removes the resource entry."""
        template_name = "test-template"
        config = {
            "roles": {
                "admin": {"permissions": {"reports": ["read"]}}  # Only one permission
            }
        }

        # Create template
        role_template_service.create_role_template(template_name, config)

        # Remove the only permission
        success = role_template_service.remove_permission_from_template(
            template_name, "admin", "reports", "read"
        )

        assert success is True

        # Verify resource entry was removed
        updated_config = role_template_service.get_role_template(template_name)
        assert "reports" not in updated_config["roles"]["admin"]["permissions"]

    def test_template_with_complex_permissions(self, temp_templates_dir):
        """Test template with complex permission structure."""
        template_name = "complex-template"
        complex_config = {
            "roles": {
                "super-admin": {
                    "description": "Super administrator with all permissions",
                    "permissions": {
                        "users": ["read", "write", "delete", "create", "manage"],
                        "projects": ["read", "write", "delete", "create", "archive"],
                        "documents": ["read", "write", "delete", "create", "version"],
                        "reports": [
                            "read",
                            "write",
                            "delete",
                            "create",
                            "export",
                            "schedule",
                        ],
                        "settings": ["read", "write", "delete", "create", "reset"],
                    },
                },
                "limited-admin": {
                    "description": "Limited administrator",
                    "permissions": {
                        "users": ["read", "write"],
                        "projects": ["read", "write", "create"],
                        "documents": ["read", "write", "create"],
                        "reports": ["read", "write"],
                    },
                },
            }
        }

        # Create template
        success = role_template_service.create_role_template(
            template_name, complex_config
        )
        assert success is True

        # Verify template was created correctly
        loaded_config = role_template_service.get_role_template(template_name)
        assert loaded_config == complex_config

        # Test adding permission to complex template
        success = role_template_service.add_permission_to_template(
            template_name, "super-admin", "analytics", "dashboard"
        )
        assert success is True

        # Verify new permission was added
        updated_config = role_template_service.get_role_template(template_name)
        assert "analytics" in updated_config["roles"]["super-admin"]["permissions"]
        assert (
            "dashboard"
            in updated_config["roles"]["super-admin"]["permissions"]["analytics"]
        )
