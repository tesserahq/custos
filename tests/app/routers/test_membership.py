import pytest
from unittest.mock import patch
from uuid import uuid4
from app.services.membership_service import MembershipService
from app.schemas.membership import MembershipCreate


class TestMembershipRouter:
    """Test cases for the membership endpoints."""

    def test_get_membership_success(self, client, db, setup_user, setup_role):
        """Test retrieving a membership by ID."""
        # Create a membership
        membership_service = MembershipService(db)
        membership = membership_service.create_membership(
            MembershipCreate(user_id=setup_user.id, role_id=setup_role.id)
        )

        response = client.get(f"/memberships/{membership.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(membership.id)
        assert data["user_id"] == str(membership.user_id)
        assert data["role_id"] == str(membership.role_id)

    def test_get_membership_not_found(self, client):
        """Test retrieving a non-existent membership."""
        non_existent_id = uuid4()
        response = client.get(f"/memberships/{non_existent_id}")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_membership_invalid_uuid(self, client):
        """Test retrieving a membership with invalid UUID format."""
        response = client.get("/memberships/invalid-uuid")
        assert response.status_code == 422

    @patch("app.commands.binding.delete_binding_command.get_casbin_service")
    def test_delete_membership_success(
        self, mock_get_casbin_service, client_another_user, db, setup_user, setup_role
    ):
        """Test that a user can delete another user's membership."""
        # Create a membership for setup_user
        membership_service = MembershipService(db)
        membership = membership_service.create_membership(
            MembershipCreate(user_id=setup_user.id, role_id=setup_role.id)
        )

        # Mock Casbin service
        mock_casbin_service = mock_get_casbin_service.return_value
        mock_casbin_service.remove_role.return_value = True

        # client_another_user tries to delete setup_user's membership
        response = client_another_user.delete(f"/memberships/{membership.id}")
        assert response.status_code == 204

        # Verify membership was deleted
        deleted_membership = membership_service.get_membership(membership.id)
        assert deleted_membership is None

    @patch("app.commands.binding.delete_binding_command.get_casbin_service")
    def test_delete_membership_prevents_self_removal(
        self, mock_get_casbin_service, client, db, setup_user, setup_role
    ):
        """Test that a user cannot delete their own membership."""
        # Create a membership for setup_user (same as the client user)
        membership_service = MembershipService(db)
        membership = membership_service.create_membership(
            MembershipCreate(user_id=setup_user.id, role_id=setup_role.id)
        )

        # Mock Casbin service (should not be called)
        mock_casbin_service = mock_get_casbin_service.return_value
        mock_casbin_service.remove_role.return_value = True

        # setup_user tries to delete their own membership
        response = client.delete(f"/memberships/{membership.id}")
        assert response.status_code == 403
        data = response.json()
        assert "cannot remove yourself" in data["detail"].lower()
        assert "another user must do it" in data["detail"].lower()

        # Verify membership was NOT deleted
        existing_membership = membership_service.get_membership(membership.id)
        assert existing_membership is not None
        assert existing_membership.id == membership.id

        # Verify Casbin was not called
        mock_casbin_service.remove_role.assert_not_called()

    def test_delete_membership_not_found(self, client):
        """Test deleting a non-existent membership."""
        non_existent_id = uuid4()
        response = client.delete(f"/memberships/{non_existent_id}")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_delete_membership_invalid_uuid(self, client):
        """Test deleting a membership with invalid UUID format."""
        response = client.delete("/memberships/invalid-uuid")
        assert response.status_code == 422
