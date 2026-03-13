from uuid import uuid4
from unittest.mock import patch
from app.repositories.membership_repository import MembershipRepository
from app.schemas.membership import MembershipCreate
from app.models.user import User


class TestUserRouter:
    """Test cases for the user endpoints."""

    def test_list_users_empty(self, client):
        """Test listing users when no users exist."""
        response = client.get("/users/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) == 1
        assert "total" in data
        assert data["total"] == 1

    def test_list_users_with_data(self, client, setup_user):
        """Test listing users when users exist."""
        response = client.get("/users/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) >= 1
        assert any(user["id"] == str(setup_user.id) for user in data["items"])
        assert "total" in data
        assert data["total"] >= 1

    def test_list_users_with_pagination(self, client, setup_user, setup_another_user):
        """Test listing users with pagination parameters."""
        response = client.get("/users/?page=1&size=1")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert "page" in data
        assert "size" in data
        assert "pages" in data

        response = client.get("/users/?page=2&size=1")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) <= 1

    def test_list_users_search_by_email(self, client, db, faker):
        """Test listing users filtered by the q search param (email)."""
        token = "zz_unique_search_token_123"

        user = User(
            email=f"{token}@example.com",
            first_name=faker.first_name(),
            last_name=faker.last_name(),
            provider="google",
            external_id=faker.uuid4(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        response = client.get(f"/users/?q={token}")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(user.id)

    def test_list_users_search_by_name(self, client, db, faker):
        """Test listing users filtered by the q search param (first/last name)."""
        first_token = "UniqueFirstToken"
        last_token = "UniqueLastToken"

        user = User(
            email=f"{faker.uuid4()}@example.com",
            first_name=first_token,
            last_name=last_token,
            provider="google",
            external_id=faker.uuid4(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        response = client.get(f"/users/?q={last_token}")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(user.id)

        response = client.get(f"/users/?q={first_token.lower()}")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(user.id)

    def test_list_users_search_no_matches(self, client):
        """Test listing users filtered by q when there are no matches."""
        response = client.get("/users/?q=definitely_no_match_zz_999999")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert data["items"] == []

    def test_get_user_success(self, client, setup_user):
        """Test retrieving a user by ID."""
        response = client.get(f"/users/{setup_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(setup_user.id)
        assert data["email"] == setup_user.email
        assert data["first_name"] == setup_user.first_name
        assert data["last_name"] == setup_user.last_name
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_user_not_found(self, client):
        """Test retrieving a non-existent user."""
        non_existent_id = uuid4()
        response = client.get(f"/users/{non_existent_id}")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_list_users_invalid_pagination(self, client):
        """Test listing users with invalid pagination parameters."""
        # Negative page
        response = client.get("/users/?page=-1")
        assert response.status_code == 422

        # Zero size
        response = client.get("/users/?size=0")
        assert response.status_code == 422

    def test_get_user_invalid_uuid(self, client):
        """Test retrieving a user with invalid UUID format."""
        response = client.get("/users/invalid-uuid")
        assert response.status_code == 422

    def test_list_users_ordered_by_updated_at(
        self, client, db, setup_user, setup_another_user, faker
    ):
        """Test that users are ordered by updated_at descending."""
        from datetime import datetime, timezone
        from app.models.user import User

        # Update the second user to have a more recent updated_at
        setup_another_user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(setup_another_user)

        response = client.get("/users/")
        assert response.status_code == 200
        data = response.json()
        items = data["items"]

        # If we have multiple users, check that they're ordered by updated_at desc
        if len(items) >= 2:
            # The most recently updated user should be first
            first_user_updated_at = items[0]["updated_at"]
            second_user_updated_at = items[1]["updated_at"]
            assert first_user_updated_at >= second_user_updated_at

    def test_list_user_memberships_empty(self, client, setup_user):
        """Test listing memberships when user has no memberships."""
        response = client.get(f"/users/{setup_user.id}/memberships")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) == 0
        assert "total" in data
        assert data["total"] == 0

    def test_list_user_memberships_with_data(self, client, db, setup_user, setup_role):
        """Test listing memberships when user has memberships."""
        # Create a membership for the user
        membership_repository = MembershipRepository(db)
        membership = membership_repository.create_membership(
            MembershipCreate(user_id=setup_user.id, role_id=setup_role.id)
        )

        response = client.get(f"/users/{setup_user.id}/memberships")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) >= 1
        membership_item = next(
            (memb for memb in data["items"] if memb["id"] == str(membership.id)), None
        )
        assert membership_item is not None
        assert membership_item["role_id"] == str(setup_role.id)
        # Verify role object is included
        assert "role" in membership_item
        assert membership_item["role"] is not None
        assert membership_item["role"]["id"] == str(setup_role.id)
        assert membership_item["role"]["name"] == setup_role.name
        assert membership_item["role"]["identifier"] == setup_role.identifier
        assert "total" in data
        assert data["total"] >= 1

    def test_list_user_memberships_with_pagination(
        self, client, db, setup_user, setup_role, faker
    ):
        """Test listing user memberships with pagination parameters."""
        # Create multiple memberships for the user
        membership_repository = MembershipRepository(db)
        membership1 = membership_repository.create_membership(
            MembershipCreate(user_id=setup_user.id, role_id=setup_role.id)
        )

        # Create another role for the second membership
        from app.models.role import Role

        another_role = Role(
            name=faker.word().capitalize() + "Role",
            identifier=faker.uuid4(),
            description="Another role",
        )
        db.add(another_role)
        db.commit()
        db.refresh(another_role)

        membership2 = membership_repository.create_membership(
            MembershipCreate(user_id=setup_user.id, role_id=another_role.id)
        )

        response = client.get(f"/users/{setup_user.id}/memberships?page=1&size=1")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert "page" in data
        assert "size" in data
        assert "pages" in data

        response = client.get(f"/users/{setup_user.id}/memberships?page=2&size=1")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) <= 1

    def test_list_user_memberships_user_not_found(self, client):
        """Test listing memberships for a non-existent user."""
        non_existent_id = uuid4()
        response = client.get(f"/users/{non_existent_id}/memberships")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_list_user_memberships_invalid_uuid(self, client):
        """Test listing memberships with invalid user UUID format."""
        response = client.get("/users/invalid-uuid/memberships")
        assert response.status_code == 422

    def test_list_user_memberships_only_returns_user_memberships(
        self, client, db, setup_user, setup_another_user, setup_role
    ):
        """Test that user memberships endpoint only returns memberships for the specified user."""
        membership_repository = MembershipRepository(db)

        # Create membership for setup_user
        user_membership = membership_repository.create_membership(
            MembershipCreate(user_id=setup_user.id, role_id=setup_role.id)
        )

        # Create membership for another user
        another_user_membership = membership_repository.create_membership(
            MembershipCreate(user_id=setup_another_user.id, role_id=setup_role.id)
        )

        # Get memberships for setup_user
        response = client.get(f"/users/{setup_user.id}/memberships")
        assert response.status_code == 200
        data = response.json()
        items = data["items"]

        # Should only contain setup_user's membership
        membership_ids = [item["id"] for item in items]
        assert str(user_membership.id) in membership_ids
        assert str(another_user_membership.id) not in membership_ids

    @patch("app.routers.user.get_casbin_repository")
    def test_check_user_permission_allowed(
        self, mock_get_casbin_repository, client, setup_user
    ):
        """Test checking user permission when allowed."""
        # Mock Casbin repository
        mock_casbin_repository = mock_get_casbin_repository.return_value
        mock_casbin_repository.authorize.return_value = True

        request_data = {
            "resource": "custos.user",
            "action": "read",
            "domain": "*",
        }

        response = client.post(
            f"/users/{setup_user.id}/permission-checks", json=request_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is True
        assert data["user_id"] == str(setup_user.id)
        assert data["resource"] == request_data["resource"]
        assert data["action"] == request_data["action"]
        assert data["domain"] == request_data["domain"]
        assert data["reason"] is None

        # Verify Casbin repository was called with correct parameters
        mock_casbin_repository.authorize.assert_called_once_with(
            user_id=str(setup_user.id),
            action=request_data["action"],
            resource=request_data["resource"],
            domain=request_data["domain"],
        )

    @patch("app.routers.user.get_casbin_repository")
    def test_check_user_permission_denied(
        self, mock_get_casbin_repository, client, setup_user
    ):
        """Test checking user permission when denied."""
        # Mock Casbin repository
        mock_casbin_repository = mock_get_casbin_repository.return_value
        mock_casbin_repository.authorize.return_value = False

        request_data = {
            "resource": "custos.user",
            "action": "write",
            "domain": "some-domain-uuid",
        }

        response = client.post(
            f"/users/{setup_user.id}/permission-checks", json=request_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is False
        assert data["user_id"] == str(setup_user.id)
        assert data["resource"] == request_data["resource"]
        assert data["action"] == request_data["action"]
        assert data["domain"] == request_data["domain"]
        assert data["reason"] == "Access denied by policy"

    @patch("app.routers.user.get_casbin_repository")
    def test_check_user_permission_default_domain(
        self, mock_get_casbin_repository, client, setup_user
    ):
        """Test checking user permission with default domain when domain is not provided."""
        # Mock Casbin repository
        mock_casbin_repository = mock_get_casbin_repository.return_value
        mock_casbin_repository.authorize.return_value = True

        request_data = {
            "resource": "custos.user",
            "action": "read",
        }

        response = client.post(
            f"/users/{setup_user.id}/permission-checks", json=request_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is True
        assert data["domain"] == "*"  # Should default to "*"

        # Verify Casbin repository was called with "*" as domain
        mock_casbin_repository.authorize.assert_called_once_with(
            user_id=str(setup_user.id),
            action=request_data["action"],
            resource=request_data["resource"],
            domain="*",
        )

    def test_check_user_permission_user_not_found(self, client):
        """Test checking permission for a non-existent user."""
        non_existent_id = uuid4()
        request_data = {
            "resource": "custos.user",
            "action": "read",
            "domain": "*",
        }

        response = client.post(
            f"/users/{non_existent_id}/permission-checks", json=request_data
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_check_user_permission_invalid_uuid(self, client):
        """Test checking permission with invalid user UUID format."""
        request_data = {
            "resource": "custos.user",
            "action": "read",
            "domain": "*",
        }

        response = client.post(
            "/users/invalid-uuid/permission-checks", json=request_data
        )
        assert response.status_code == 422

    def test_check_user_permission_missing_fields(self, client, setup_user):
        """Test checking permission with missing required fields."""
        # Missing resource
        request_data = {
            "action": "read",
            "domain": "*",
        }
        response = client.post(
            f"/users/{setup_user.id}/permission-checks", json=request_data
        )
        assert response.status_code == 422

        # Missing action
        request_data = {
            "resource": "custos.user",
            "domain": "*",
        }
        response = client.post(
            f"/users/{setup_user.id}/permission-checks", json=request_data
        )
        assert response.status_code == 422
