from unittest.mock import patch
from uuid import uuid4
from app.repositories.membership_repository import MembershipRepository
from app.schemas.membership import MembershipCreate


class TestMembershipRouter:
    """Test cases for the membership endpoints."""

    def test_get_membership_success(self, client, db, setup_user, setup_role):
        """Test retrieving a membership by ID."""
        # Create a membership
        membership_repository = MembershipRepository(db)
        membership = membership_repository.create_membership(
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

    @patch("app.commands.memberships.delete_membership_command.get_casbin_repository")
    def test_delete_membership_success(
        self,
        mock_get_casbin_repository,
        client_another_user,
        db,
        setup_user,
        setup_role,
    ):
        """Test that a user can delete another user's membership."""
        # Create a membership for setup_user
        membership_repository = MembershipRepository(db)
        membership = membership_repository.create_membership(
            MembershipCreate(user_id=setup_user.id, role_id=setup_role.id)
        )

        # Mock Casbin service
        mock_casbin_repository = mock_get_casbin_repository.return_value  # noqa: F841
        mock_casbin_repository.remove_role.return_value = True

        # client_another_user tries to delete setup_user's membership
        response = client_another_user.delete(f"/memberships/{membership.id}")
        assert response.status_code == 204

        # Verify membership was deleted
        deleted_membership = membership_repository.get_membership(membership.id)
        assert deleted_membership is None

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
