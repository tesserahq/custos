import pytest
from unittest.mock import patch
from app.models.user import User
from app.services.casbin_service import casbin_service
import os


class TestSetupEndpoint:
    """Test cases for the setup endpoint."""

    def test_get_system_status_setup_required(self, client):
        """Test system status when no system admin exists."""
        # Clear any existing Casbin data to ensure clean state
        casbin_service.clear_all_policies()

        response = client.get("/setup/system-status")
        assert response.status_code == 200
        data = response.json()
        assert data["setup_required"] is True
        assert "System administrator has not been set up" in data["message"]

    def test_get_system_status_setup_completed(self, client, db, setup_user):
        """Test system status when system admin exists."""
        # Set up a system admin user
        os.environ["SUPER_USER_EMAIL"] = setup_user.email
        setup_response = client.post("/setup")
        assert setup_response.status_code == 200

        # Check system status
        response = client.get("/setup/system-status")
        assert response.status_code == 200
        data = response.json()
        assert data["setup_required"] is False
        assert "System administrator is already set up" in data["message"]
        assert "1 system admin user" in data["message"]

    def test_get_system_status_with_multiple_admins(self, client, db, setup_user):
        """Test system status when multiple system admins exist."""
        # Set up first system admin
        os.environ["SUPER_USER_EMAIL"] = setup_user.email
        setup_response = client.post("/setup")
        assert setup_response.status_code == 200

        # Create another user and assign system admin role directly
        another_user = User(
            email="another@example.com",
            username="another@example.com",
            first_name="Another",
            last_name="User",
            provider="google",
            external_id="another123",
        )
        db.add(another_user)
        db.commit()
        db.refresh(another_user)

        # Assign system admin role to the second user
        casbin_service.assign_role(str(another_user.id), "system_admin", domain="*")

        # Check system status
        response = client.get("/setup/system-status")
        assert response.status_code == 200
        data = response.json()
        assert data["setup_required"] is False
        assert "2 system admin user" in data["message"]

    def test_get_system_status_error_handling(self, client):
        """Test system status handles errors gracefully."""
        with patch(
            "app.services.casbin_service.casbin_service.get_users_for_role"
        ) as mock_get_users:
            mock_get_users.side_effect = Exception("Database connection error")

            response = client.get("/setup/system-status")
            assert response.status_code == 200
            data = response.json()
            assert data["setup_required"] is True
            assert "Error checking system status" in data["message"]

    def test_setup_system_admin_success(self, client, db, setup_user):
        """Test successful system admin setup."""
        # Set the environment variable to the user's email
        os.environ["SUPER_USER_EMAIL"] = setup_user.email

        response = client.post("/setup")
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.json()}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["super_user_email"] == setup_user.email
        assert data["user_id"] == str(setup_user.id)
        assert data["role_assigned"] == "system_admin"
        assert "System admin setup completed successfully" in data["message"]

    def test_setup_system_admin_missing_env_var(self, client):
        """Test setup fails when SUPER_USER_EMAIL is not set."""
        # Ensure the environment variable is not set
        if "SUPER_USER_EMAIL" in os.environ:
            del os.environ["SUPER_USER_EMAIL"]

        response = client.post("/setup")
        assert response.status_code == 400
        data = response.json()
        assert "SUPER_USER_EMAIL environment variable is not set" in data["detail"]

    def test_setup_system_admin_user_not_found(self, client, db):
        """Test setup fails when user with specified email doesn't exist."""
        # Set the environment variable to a non-existent email
        os.environ["SUPER_USER_EMAIL"] = "nonexistent@example.com"

        response = client.post("/setup")
        assert response.status_code == 404
        data = response.json()
        assert "No user found with email: nonexistent@example.com" in data["detail"]

    def test_setup_system_admin_role_definition_failure(self, client, db, setup_user):
        """Test setup fails when role definition fails."""
        # Set the environment variable to the user's email
        os.environ["SUPER_USER_EMAIL"] = setup_user.email

        with patch(
            "app.services.role_definition_service.role_definition_service.define_system_admin_role"
        ) as mock_define_role:
            mock_define_role.return_value = False
            response = client.post("/setup")
            assert response.status_code == 500
            data = response.json()
            assert "Failed to define system admin role" in data["detail"]

    def test_setup_system_admin_role_assignment_failure(self, client, db, setup_user):
        """Test setup fails when role assignment fails."""
        # Set the environment variable to the user's email
        os.environ["SUPER_USER_EMAIL"] = setup_user.email

        with patch(
            "app.services.casbin_service.casbin_service.assign_role"
        ) as mock_assign_role:
            mock_assign_role.return_value = False
            response = client.post("/setup")
            assert response.status_code == 500
            data = response.json()
            assert "Failed to assign system admin role to user" in data["detail"]

    def test_setup_system_admin_unexpected_error(self, client, db, setup_user):
        """Test setup handles unexpected errors gracefully."""
        # Set the environment variable to the user's email
        os.environ["SUPER_USER_EMAIL"] = setup_user.email

        with patch(
            "app.services.role_definition_service.role_definition_service.define_system_admin_role"
        ) as mock_define_role:
            mock_define_role.side_effect = Exception("Unexpected database error")
            response = client.post("/setup")
            assert response.status_code == 500
            data = response.json()
            assert "Unexpected error during system admin setup" in data["detail"]
            assert "Unexpected database error" in data["detail"]

    def test_setup_system_admin_real_casbin_integration(self, client, db, setup_user):
        """Test setup with real Casbin integration (integration test)."""
        # Set the environment variable to the user's email
        os.environ["SUPER_USER_EMAIL"] = setup_user.email

        response = client.post("/setup")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["super_user_email"] == setup_user.email
        assert data["user_id"] == str(setup_user.id)
        assert data["role_assigned"] == "system_admin"
        user_roles = casbin_service.get_user_roles(str(setup_user.id), domain="*")
        assert "system_admin" in user_roles
        permissions = casbin_service.get_user_permissions(
            str(setup_user.id), domain="*"
        )
        assert len(permissions) > 0
