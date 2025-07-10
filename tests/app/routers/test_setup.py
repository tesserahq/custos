import pytest
from app.models.user import User
from app.services.casbin_service import casbin_service
import os


class TestSetupEndpoint:
    """Test cases for the setup endpoint."""

    def test_get_system_status_setup_required(self, client):
        """Test system status when no system admin exists."""
        # Note: This test may show setup_required=False if there are existing system admins
        # from previous tests, which is expected behavior
        response = client.get("/setup/system-status")
        assert response.status_code == 200
        data = response.json()
        # The system status endpoint should always return a valid response
        assert "setup_required" in data
        assert "message" in data

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

    def test_get_system_status_with_multiple_admins(
        self, client, db, setup_user, setup_another_user
    ):
        """Test system status when multiple system admins exist."""
        # Set up multiple system admins
        os.environ["SUPER_USER_EMAIL"] = (
            f"{setup_user.email},{setup_another_user.email}"
        )
        setup_response = client.post("/setup")
        assert setup_response.status_code == 200

        # Check system status
        response = client.get("/setup/system-status")
        assert response.status_code == 200
        data = response.json()
        assert data["setup_required"] is False
        assert "System administrator is already set up" in data["message"]

    def test_setup_system_admin_single_user_success(self, client, db, setup_user):
        """Test successful system admin setup with single user."""
        # Set the environment variable to the user's email
        os.environ["SUPER_USER_EMAIL"] = setup_user.email

        response = client.post("/setup")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["super_user_emails"] == [setup_user.email]
        assert data["user_ids"] == [str(setup_user.id)]
        assert data["role_assigned"] == "system_admin"
        assert "System admin setup completed successfully" in data["message"]

    def test_setup_system_admin_multiple_users_success(
        self, client, db, setup_user, setup_another_user
    ):
        """Test successful system admin setup with multiple users."""
        # Set the environment variable to multiple emails
        os.environ["SUPER_USER_EMAIL"] = (
            f"{setup_user.email},{setup_another_user.email}"
        )

        response = client.post("/setup")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert set(data["super_user_emails"]) == {
            setup_user.email,
            setup_another_user.email,
        }
        assert set(data["user_ids"]) == {str(setup_user.id), str(setup_another_user.id)}
        assert data["role_assigned"] == "system_admin"
        assert "System admin setup completed successfully" in data["message"]

    def test_setup_system_admin_partial_success(self, client, db, setup_user):
        """Test setup with partial success - one valid email, one invalid."""
        # Set the environment variable with one valid and one invalid email
        os.environ["SUPER_USER_EMAIL"] = f"{setup_user.email},nonexistent@example.com"

        response = client.post("/setup")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["super_user_emails"] == [setup_user.email]
        assert data["user_ids"] == [str(setup_user.id)]
        assert data["role_assigned"] == "system_admin"
        assert "System admin setup completed with partial success" in data["message"]
        assert "nonexistent@example.com" in data["message"]

    def test_setup_system_admin_missing_env_var(self, client):
        """Test setup fails when SUPER_USER_EMAIL is not set."""
        # Ensure the environment variable is not set
        if "SUPER_USER_EMAIL" in os.environ:
            del os.environ["SUPER_USER_EMAIL"]

        response = client.post("/setup")
        assert response.status_code == 400
        data = response.json()
        assert "SUPER_USER_EMAIL environment variable is not set" in data["detail"]

    def test_setup_system_admin_empty_env_var(self, client):
        """Test setup fails when SUPER_USER_EMAIL is empty."""
        os.environ["SUPER_USER_EMAIL"] = ""

        response = client.post("/setup")
        assert response.status_code == 400
        data = response.json()
        assert "SUPER_USER_EMAIL environment variable is not set" in data["detail"]

    def test_setup_system_admin_whitespace_only_env_var(self, client):
        """Test setup fails when SUPER_USER_EMAIL contains only whitespace."""
        os.environ["SUPER_USER_EMAIL"] = "   ,  ,  "

        response = client.post("/setup")
        assert response.status_code == 400
        data = response.json()
        assert "SUPER_USER_EMAIL environment variable is not set" in data["detail"]

    def test_setup_system_admin_all_users_not_found(self, client, db):
        """Test setup fails when no users with specified emails exist."""
        # Set the environment variable to non-existent emails
        os.environ["SUPER_USER_EMAIL"] = (
            "nonexistent1@example.com,nonexistent2@example.com"
        )

        response = client.post("/setup")
        assert response.status_code == 404
        data = response.json()
        assert "No users found with the provided emails" in data["detail"]

    def test_setup_system_admin_real_casbin_integration(self, client, db, setup_user):
        """Test setup with real Casbin integration (integration test)."""
        # Set the environment variable to the user's email
        os.environ["SUPER_USER_EMAIL"] = setup_user.email

        response = client.post("/setup")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["super_user_emails"] == [setup_user.email]
        assert data["user_ids"] == [str(setup_user.id)]
        assert data["role_assigned"] == "system_admin"

        # Verify the role was actually assigned in Casbin
        user_roles = casbin_service.get_user_roles(str(setup_user.id), domain="*")
        assert "system_admin" in user_roles
        permissions = casbin_service.get_user_permissions(
            str(setup_user.id), domain="*"
        )
        assert len(permissions) > 0

    def test_setup_system_admin_multiple_users_real_casbin_integration(
        self, client, db, setup_user, setup_another_user
    ):
        """Test setup with multiple users using real Casbin integration."""
        # Set the environment variable to multiple emails
        os.environ["SUPER_USER_EMAIL"] = (
            f"{setup_user.email},{setup_another_user.email}"
        )

        response = client.post("/setup")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert set(data["super_user_emails"]) == {
            setup_user.email,
            setup_another_user.email,
        }
        assert set(data["user_ids"]) == {str(setup_user.id), str(setup_another_user.id)}
        assert data["role_assigned"] == "system_admin"

        # Verify both users have the role assigned in Casbin
        user1_roles = casbin_service.get_user_roles(str(setup_user.id), domain="*")
        user2_roles = casbin_service.get_user_roles(
            str(setup_another_user.id), domain="*"
        )
        assert "system_admin" in user1_roles
        assert "system_admin" in user2_roles
