import pytest
from app.services.role_config_service import role_config_service
from app.services.casbin_service import casbin_service
from app.schemas.authorization import SetupRolesRequest
import json


class TestRoleConfig:
    """Test cases for configuration-based role definition functionality."""

    def test_load_roles_from_yaml(self):
        """Test loading role definitions from YAML configuration."""
        config = role_config_service.load_roles_from_yaml("roles.yaml")

        # Check that config has expected structure
        assert "roles" in config
        assert "admin" in config["roles"]
        assert "editor" in config["roles"]
        assert "viewer" in config["roles"]

        # Check admin role permissions
        admin_permissions = config["roles"]["admin"]["permissions"]
        assert "users" in admin_permissions
        assert "read" in admin_permissions["users"]
        assert "write" in admin_permissions["users"]
        assert "delete" in admin_permissions["users"]
        assert "create" in admin_permissions["users"]

    def test_load_roles_from_yaml_content(self):
        """Test loading role definitions from YAML content string."""
        yaml_content = """
roles:
  admin:
    description: "Full system access"
    permissions:
      users:
        - read
        - write
        - delete
        - create
      projects:
        - read
        - write
  editor:
    description: "Content editing"
    permissions:
      projects:
        - read
        - write
        - create
"""
        config = role_config_service.load_roles_from_yaml_content(yaml_content)

        # Check that config has expected structure
        assert "roles" in config
        assert "admin" in config["roles"]
        assert "editor" in config["roles"]

        # Check admin role permissions
        admin_permissions = config["roles"]["admin"]["permissions"]
        assert "users" in admin_permissions
        assert "read" in admin_permissions["users"]
        assert "write" in admin_permissions["users"]

    def test_load_roles_from_csv(self):
        """Test loading role definitions from CSV configuration."""
        policies = role_config_service.load_roles_from_csv("roles.csv")

        # Check that we have policies
        assert len(policies) > 0

        # Check policy format (p, role, domain, resource, action)
        for policy in policies:
            assert len(policy) >= 5
            assert policy[0] == "p"  # policy type
            assert policy[1] in ["admin", "editor", "viewer", "moderator"]  # role
            assert policy[2] == "*"  # domain (wildcard)
            assert policy[3] in [
                "users",
                "projects",
                "documents",
                "roles",
                "settings",
                "comments",
            ]  # resource
            assert policy[4] in ["read", "write", "delete", "create"]  # action

    def test_define_roles_from_yaml(self, client):
        """Test defining roles from YAML configuration."""
        domain = "test-domain-yaml-config"

        # Define roles from YAML
        results = role_config_service.define_roles_from_yaml(domain, "roles.yaml")

        # All roles should be created successfully
        assert results["admin"] is True
        assert results["editor"] is True
        assert results["viewer"] is True
        assert results["moderator"] is True

        # Check that roles have expected permissions
        admin_permissions = role_config_service._define_role_permissions(
            "admin", domain, []
        )
        assert admin_permissions is True

    def test_define_roles_from_yaml_content(self, client):
        """Test defining roles from YAML content string."""
        domain = "test-domain-yaml-content"
        yaml_content = """
roles:
  admin:
    description: "Full system access"
    permissions:
      users:
        - read
        - write
        - delete
        - create
      projects:
        - read
        - write
  editor:
    description: "Content editing"
    permissions:
      projects:
        - read
        - write
        - create
      documents:
        - read
        - write
"""

        # Define roles from YAML content
        results = role_config_service.define_roles_from_yaml_content(
            domain, yaml_content
        )

        # Roles should be created successfully
        assert results["admin"] is True
        assert results["editor"] is True

    def test_define_roles_from_csv(self, client):
        """Test defining roles from CSV configuration."""
        domain = "test-domain-csv-config"

        # Define roles from CSV
        results = role_config_service.define_roles_from_csv(domain, "roles.csv")

        # All roles should be created successfully
        assert results["admin"] is True
        assert results["editor"] is True
        assert results["viewer"] is True
        assert results["moderator"] is True

    def test_get_available_roles(self):
        """Test getting available roles from configuration files."""
        # Test YAML
        yaml_roles = role_config_service.get_available_roles("roles.yaml")
        assert "admin" in yaml_roles
        assert "editor" in yaml_roles
        assert "viewer" in yaml_roles
        assert "moderator" in yaml_roles
        assert len(yaml_roles) == 4

        # Test CSV
        csv_roles = role_config_service.get_available_roles("roles.csv")
        assert "admin" in csv_roles
        assert "editor" in csv_roles
        assert "viewer" in csv_roles
        assert "moderator" in csv_roles
        assert len(csv_roles) == 4

    def test_validate_yaml_configuration(self):
        """Test YAML configuration validation."""
        validation = role_config_service.validate_configuration("roles.yaml")

        assert validation["valid"] is True
        assert len(validation["errors"]) == 0

    def test_validate_yaml_content(self):
        """Test YAML content validation."""
        yaml_content = """
roles:
  admin:
    description: "Full system access"
    permissions:
      users:
        - read
        - write
        - delete
        - create
      projects:
        - read
        - write
  editor:
    description: "Content editing"
    permissions:
      projects:
        - read
        - write
        - create
"""
        validation = role_config_service.validate_yaml_content(yaml_content)

        assert validation["valid"] is True
        assert len(validation["errors"]) == 0
        assert "admin" in validation["available_roles"]
        assert "editor" in validation["available_roles"]
        assert (
            validation["total_permissions"] == 9
        )  # 4 for admin users + 2 for admin projects + 3 for editor projects

    def test_validate_invalid_yaml_content(self):
        """Test validation of invalid YAML content."""
        invalid_yaml = """
roles:
  admin:
    permissions:
      users: "not a list"  # Should be a list
"""
        validation = role_config_service.validate_yaml_content(invalid_yaml)

        assert validation["valid"] is False
        assert len(validation["errors"]) > 0

    def test_validate_csv_configuration(self):
        """Test CSV configuration validation."""
        validation = role_config_service.validate_configuration("roles.csv")

        assert validation["valid"] is True
        assert len(validation["errors"]) == 0

    def test_role_authorization_flow_with_config(self, client, user_id):
        """Test complete role authorization flow using configuration-based roles."""
        domain = "test-domain-config-flow"

        # 1. Set up roles from YAML configuration
        role_config_service.define_roles_from_yaml(domain, "roles.yaml")

        # 2. Assign admin role to user
        success = casbin_service.assign_role(user_id, "admin", domain)
        assert success is True

        # 3. Check authorization for admin permissions
        # Should be able to delete users
        allowed = casbin_service.authorize(user_id, "delete", "users", domain)
        assert allowed is True

        # Should be able to create projects
        allowed = casbin_service.authorize(user_id, "create", "projects", domain)
        assert allowed is True

        # 4. Assign moderator role to another user
        user2_id = "auth0|user2"
        success = casbin_service.assign_role(user2_id, "moderator", domain)
        assert success is True

        # 5. Check authorization for moderator permissions
        # Should be able to read users
        allowed = casbin_service.authorize(user2_id, "read", "users", domain)
        assert allowed is True

        # Should be able to write comments
        allowed = casbin_service.authorize(user2_id, "write", "comments", domain)
        assert allowed is True

        # Should be able to delete comments
        allowed = casbin_service.authorize(user2_id, "delete", "comments", domain)
        assert allowed is True

        # Should NOT be able to delete users
        allowed = casbin_service.authorize(user2_id, "delete", "users", domain)
        assert allowed is False

    def test_role_authorization_flow_with_yaml_content(self, client, user_id):
        """Test complete role authorization flow using YAML content."""
        domain = "test-domain-yaml-content-flow"
        yaml_content = """
roles:
  admin:
    description: "Full system access"
    permissions:
      users:
        - read
        - write
        - delete
        - create
      projects:
        - read
        - write
        - delete
        - create
  editor:
    description: "Content editing"
    permissions:
      users:
        - read
      projects:
        - read
        - write
        - create
      documents:
        - read
        - write
        - create
"""

        # 1. Set up roles from YAML content
        results = role_config_service.define_roles_from_yaml_content(
            domain, yaml_content
        )
        assert results["admin"] is True
        assert results["editor"] is True

        # 2. Assign admin role to user
        success = casbin_service.assign_role(user_id, "admin", domain)
        assert success is True

        # 3. Check authorization for admin permissions
        allowed = casbin_service.authorize(user_id, "delete", "users", domain)
        assert allowed is True

        allowed = casbin_service.authorize(user_id, "create", "projects", domain)
        assert allowed is True

        # 4. Assign editor role to another user
        user2_id = "auth0|user2"
        success = casbin_service.assign_role(user2_id, "editor", domain)
        assert success is True

        # 5. Check authorization for editor permissions
        allowed = casbin_service.authorize(user2_id, "read", "users", domain)
        assert allowed is True

        allowed = casbin_service.authorize(user2_id, "write", "documents", domain)
        assert allowed is True

        # Should NOT be able to delete users
        allowed = casbin_service.authorize(user2_id, "delete", "users", domain)
        assert allowed is False

    def test_configuration_vs_hardcoded_equivalence(self, client):
        """Test that configuration-based roles are equivalent to hardcoded roles."""
        domain_config = "test-domain-config"
        domain_hardcoded = "test-domain-hardcoded"

        # Set up roles using configuration
        config_results = role_config_service.define_roles_from_yaml(
            domain_config, "roles.yaml"
        )

        # Set up roles using hardcoded approach
        from app.services.role_definition_service import role_definition_service

        hardcoded_results = role_definition_service.setup_default_roles(
            domain_hardcoded
        )

        # Both should succeed
        assert config_results["admin"] is True
        assert hardcoded_results["admin"] is True

        # Check that permissions are equivalent
        config_admin_perms = role_definition_service.get_role_permissions(
            "admin", domain_config
        )
        hardcoded_admin_perms = role_definition_service.get_role_permissions(
            "admin", domain_hardcoded
        )

        # Convert to sets for comparison
        config_perms_set = set(config_admin_perms)
        hardcoded_perms_set = set(hardcoded_admin_perms)

        # Core permissions should be the same
        core_permissions = {
            ("users", "read"),
            ("users", "write"),
            ("users", "delete"),
            ("users", "create"),
        }
        assert core_permissions.issubset(config_perms_set)
        assert core_permissions.issubset(hardcoded_perms_set)

    def test_setup_roles_yaml(self, client):
        """Test setting up roles using YAML content via the unified endpoint."""
        yaml_content = """
roles:
  admin:
    description: "Full system access"
    permissions:
      users:
        - read
        - write
        - delete
        - create
      projects:
        - read
        - write
  editor:
    description: "Content editing"
    permissions:
      projects:
        - read
        - write
        - create
"""
        req = {
            "domain": "test-domain-unified-yaml",
            "type": "yaml",
            "content": yaml_content,
        }
        resp = client.post("/authorization/setup-roles", json=req)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["results"]["admin"] is True
        assert data["results"]["editor"] is True
        assert data["success_count"] == 2
        assert data["total_roles"] == 2

    def test_setup_roles_csv(self, client):
        """Test setting up roles using CSV content via the unified endpoint."""
        csv_content = """p,admin,*,users,read\np,admin,*,users,write\np,editor,*,projects,read\np,editor,*,projects,write\np,editor,*,projects,create\n"""
        req = {
            "domain": "test-domain-unified-csv",
            "type": "csv",
            "content": csv_content,
        }
        resp = client.post("/authorization/setup-roles", json=req)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["results"]["admin"] is True
        assert data["results"]["editor"] is True
        assert data["success_count"] == 2
        assert data["total_roles"] == 2

    def test_setup_roles_invalid_type(self, client):
        """Test setup-roles endpoint with an invalid type."""
        req = {
            "domain": "test-domain-invalid-type",
            "type": "invalid_type",
            "content": "some content",
        }
        resp = client.post("/authorization/setup-roles", json=req)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert data["validation_errors"]
        assert "Invalid type" in data["validation_errors"][0]
