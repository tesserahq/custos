import pytest
from app.services.role_definition_service import role_definition_service
from app.services.casbin_service import casbin_service


class TestRoleDefinition:
    """Test cases for role definition functionality."""

    def test_define_admin_role(self, client):
        """Test defining admin role with full permissions."""
        domain = "test-domain-admin"

        # Define admin role
        success = role_definition_service.define_admin_role(domain)
        assert success is True

        # Check that admin role has expected permissions
        permissions = role_definition_service.get_role_permissions("admin", domain)

        # Should have user management permissions
        assert ("users", "read") in permissions
        assert ("users", "write") in permissions
        assert ("users", "delete") in permissions
        assert ("users", "create") in permissions

        # Should have project management permissions
        assert ("projects", "read") in permissions
        assert ("projects", "write") in permissions
        assert ("projects", "delete") in permissions
        assert ("projects", "create") in permissions

        # Should have document management permissions
        assert ("documents", "read") in permissions
        assert ("documents", "write") in permissions
        assert ("documents", "delete") in permissions
        assert ("documents", "create") in permissions

    def test_define_editor_role(self, client):
        """Test defining editor role with read/write permissions."""
        domain = "test-domain-editor"

        # Define editor role
        success = role_definition_service.define_editor_role(domain)
        assert success is True

        # Check that editor role has expected permissions
        permissions = role_definition_service.get_role_permissions("editor", domain)

        # Should have read-only user management
        assert ("users", "read") in permissions
        assert ("users", "write") not in permissions  # Should not have write
        assert ("users", "delete") not in permissions  # Should not have delete

        # Should have project management permissions
        assert ("projects", "read") in permissions
        assert ("projects", "write") in permissions
        assert ("projects", "create") in permissions
        assert ("projects", "delete") not in permissions  # Should not have delete

        # Should have document management permissions
        assert ("documents", "read") in permissions
        assert ("documents", "write") in permissions
        assert ("documents", "create") in permissions

    def test_define_viewer_role(self, client):
        """Test defining viewer role with read-only permissions."""
        domain = "test-domain-viewer"

        # Define viewer role
        success = role_definition_service.define_viewer_role(domain)
        assert success is True

        # Check that viewer role has expected permissions
        permissions = role_definition_service.get_role_permissions("viewer", domain)

        # Should only have read permissions
        assert ("users", "read") in permissions
        assert ("users", "write") not in permissions
        assert ("users", "delete") not in permissions
        assert ("users", "create") not in permissions

        assert ("projects", "read") in permissions
        assert ("projects", "write") not in permissions
        assert ("projects", "delete") not in permissions
        assert ("projects", "create") not in permissions

        assert ("documents", "read") in permissions
        assert ("documents", "write") not in permissions
        assert ("documents", "delete") not in permissions
        assert ("documents", "create") not in permissions

    def test_define_custom_role(self, client):
        """Test defining a custom role with specific permissions."""
        domain = "test-domain-custom"
        role_name = "moderator"
        custom_permissions = [
            ("users", "read"),
            ("users", "write"),
            ("comments", "read"),
            ("comments", "write"),
            ("comments", "delete"),
        ]

        # Define custom role
        success = role_definition_service.define_custom_role(
            role_name, domain, custom_permissions
        )
        assert success is True

        # Check that custom role has expected permissions
        permissions = role_definition_service.get_role_permissions(role_name, domain)

        for resource, action in custom_permissions:
            assert (resource, action) in permissions

        # Should not have permissions not explicitly granted
        assert ("users", "delete") not in permissions
        assert ("projects", "read") not in permissions

    def test_setup_default_roles(self, client):
        """Test setting up all default roles for a domain."""
        domain = "test-domain-defaults"

        # Set up default roles
        results = role_definition_service.setup_default_roles(domain)

        # All roles should be created successfully
        assert results["admin"] is True
        assert results["editor"] is True
        assert results["viewer"] is True

        # Check that all roles exist
        roles = role_definition_service.list_defined_roles(domain)
        assert "admin" in roles
        assert "editor" in roles
        assert "viewer" in roles
        assert len(roles) == 3

    def test_list_defined_roles(self, client):
        """Test listing all roles defined for a domain."""
        domain = "test-domain-list"

        # Define some roles
        role_definition_service.define_admin_role(domain)
        role_definition_service.define_custom_role(
            "moderator", domain, [("users", "read")]
        )

        # List roles
        roles = role_definition_service.list_defined_roles(domain)

        assert "admin" in roles
        assert "moderator" in roles
        assert len(roles) == 2

    def test_role_authorization_flow(self, client, user_id):
        """Test complete role authorization flow."""
        domain = "test-domain-flow"

        # 1. Set up default roles
        role_definition_service.setup_default_roles(domain)

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

        # 4. Assign editor role to another user
        user2_id = "auth0|user2"
        success = casbin_service.assign_role(user2_id, "editor", domain)
        assert success is True

        # 5. Check authorization for editor permissions
        # Should be able to read users
        allowed = casbin_service.authorize(user2_id, "read", "users", domain)
        assert allowed is True

        # Should be able to write documents
        allowed = casbin_service.authorize(user2_id, "write", "documents", domain)
        assert allowed is True

        # Should NOT be able to delete users
        allowed = casbin_service.authorize(user2_id, "delete", "users", domain)
        assert allowed is False

    def test_domain_isolation(self, client, user_id):
        """Test that roles are isolated between domains."""
        domain1 = "test-domain-1"
        domain2 = "test-domain-2"

        # Set up roles in both domains
        role_definition_service.setup_default_roles(domain1)
        role_definition_service.setup_default_roles(domain2)

        # Assign admin role in domain1
        success = casbin_service.assign_role(user_id, "admin", domain1)
        assert success is True

        # Should have admin permissions in domain1
        allowed = casbin_service.authorize(user_id, "delete", "users", domain1)
        assert allowed is True

        # Should NOT have admin permissions in domain2
        allowed = casbin_service.authorize(user_id, "delete", "users", domain2)
        assert allowed is False

        # Assign viewer role in domain2
        success = casbin_service.assign_role(user_id, "viewer", domain2)
        assert success is True

        # Should have read permissions in domain2
        allowed = casbin_service.authorize(user_id, "read", "users", domain2)
        assert allowed is True

        # Should NOT have write permissions in domain2
        allowed = casbin_service.authorize(user_id, "write", "users", domain2)
        assert allowed is False
