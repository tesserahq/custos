import pytest
from uuid import UUID
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.schemas.service_account import ServiceAccountCreate, ServiceAccountUpdate
from app.models.user import User
from app.models.service_account import ServiceAccount
from app.services.casbin_service import casbin_service
from app.services.service_account_service import ServiceAccountService


@pytest.fixture
def system_admin_user(db, faker):
    """Create a super admin user with proper Casbin roles."""
    email = faker.email()

    user_data = {
        "email": email,
        "username": email,
        "first_name": faker.first_name(),
        "last_name": faker.last_name(),
        "provider": "google",
        "external_id": faker.uuid4(),
    }

    user = User(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)

    # Assign super admin role in Casbin
    casbin_service.assign_role(user_id=str(user.id), role="system_admin", domain="*")

    return user


@pytest.fixture
def system_admin_service_account(db, faker):
    """Create a super admin service account with proper Casbin roles."""
    service = ServiceAccountService(db)

    service_account_data = ServiceAccountCreate(
        name="Super Admin Service Account",
        description="A service account with super admin privileges",
        is_active=True,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )

    # Create the service account
    created_account = service.create_service_account(
        service_account_data, created_by=None
    )

    # Assign super admin role in Casbin
    casbin_service.assign_role(
        user_id=str(created_account.id), role="system_admin", domain="*"
    )

    return created_account


@pytest.fixture
def regular_user(db, faker):
    """Create a regular user without admin privileges."""
    email = faker.email()

    user_data = {
        "email": email,
        "username": email,
        "first_name": faker.first_name(),
        "last_name": faker.last_name(),
        "provider": "google",
        "external_id": faker.uuid4(),
    }

    user = User(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)

    # Assign regular user role
    casbin_service.assign_role(user_id=str(user.id), role="user", domain="*")

    return user


@pytest.fixture
def service_account(db, faker):
    """Create a test service account."""
    service = ServiceAccountService(db)

    service_account_data = ServiceAccountCreate(
        name="Test Service Account",
        description="A test service account for testing",
        is_active=True,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )

    # Create service account (we'll need to mock the created_by for now)
    with patch(
        "app.services.service_account_service.ServiceAccountService.create_service_account"
    ) as mock_create:
        mock_account = MagicMock()
        mock_account.id = "123e4567-e89b-12d3-a456-426614174000"
        mock_account.name = "Test Service Account"
        mock_account.description = "A test service account for testing"
        mock_account.is_active = True
        mock_account.created_at = datetime.now(timezone.utc)
        mock_account.updated_at = datetime.now(timezone.utc)
        mock_create.return_value = mock_account

        return service.create_service_account(service_account_data, created_by=1)


@pytest.fixture
def client_with_system_admin(client, system_admin_user):
    """Create a test client with a super admin user."""
    # Update the app state to use the super admin user
    client.app.state.test_user = system_admin_user
    return client


@pytest.fixture
def client_with_regular_user(client, regular_user):
    """Create a test client with a regular user."""
    # Update the app state to use the regular user
    client.app.state.test_user = regular_user
    return client


@pytest.fixture
def client_with_service_account(client, system_admin_service_account):
    """Create a test client with a super admin service account."""
    # Update the app state to use the service account
    client.app.state.test_service_account = system_admin_service_account
    return client


class TestServiceAccountsEndpoints:
    """Test cases for service accounts endpoints."""

    def test_create_service_account_success(self, client_with_system_admin, db):
        """Test creating a service account successfully."""
        service_account_data = {
            "name": "Test Service Account",
            "description": "A test service account",
            "is_active": True,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        }

        response = client_with_system_admin.post(
            "/service-accounts/", json=service_account_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Service Account"
        assert data["description"] == "A test service account"
        assert data["is_active"] is True
        assert "api_key" in data
        assert data["api_key"].startswith("sk_")

    def test_create_service_account_unauthorized(self, client_with_regular_user):
        """Test creating a service account without admin privileges."""
        service_account_data = {
            "name": "Test Service Account",
            "description": "A test service account",
        }

        response = client_with_regular_user.post(
            "/service-accounts/", json=service_account_data
        )

        assert response.status_code == 403
        assert "Super admin privileges required" in response.json()["detail"]

    def test_list_service_accounts_success(self, client_with_system_admin, db):
        """Test listing service accounts successfully."""
        # First create a service account
        service = ServiceAccountService(db)
        service_account_data = ServiceAccountCreate(
            name="List Test Account",
            description="Account for list test",
            is_active=True,
        )

        with patch(
            "app.services.service_account_service.ServiceAccountService.create_service_account"
        ) as mock_create:
            mock_account = MagicMock()
            mock_account.id = "123e4567-e89b-12d3-a456-426614174001"
            mock_account.name = "List Test Account"
            mock_account.description = "Account for list test"
            mock_account.is_active = True
            mock_account.created_at = datetime.now(timezone.utc)
            mock_account.updated_at = datetime.now(timezone.utc)
            mock_create.return_value = mock_account

            service.create_service_account(service_account_data, created_by=1)

        response = client_with_system_admin.get("/service-accounts/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_service_accounts_unauthorized(self, client_with_regular_user):
        """Test listing service accounts without admin privileges."""
        response = client_with_regular_user.get("/service-accounts/")

        assert response.status_code == 403
        assert "Super admin privileges required" in response.json()["detail"]

    def test_get_service_account_success(self, client_with_system_admin, db):
        """Test getting a service account successfully."""
        # Create a real service account first
        service = ServiceAccountService(db)
        service_account_data = ServiceAccountCreate(
            name="Get Test Account",
            description="Test account for get operation",
            external_id="ext_get_123",
        )
        system_admin_user = client_with_system_admin.app.state.test_user

        created_account = service.create_service_account(
            service_account_data, created_by=system_admin_user.id
        )

        # Now get the service account via API
        response = client_with_system_admin.get(
            f"/service-accounts/{created_account.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Get Test Account"
        assert data["description"] == "Test account for get operation"

    def test_get_service_account_not_found(self, client_with_system_admin, db):
        """Test getting a non-existent service account."""
        response = client_with_system_admin.get(
            "/service-accounts/123e4567-e89b-12d3-a456-426614174000"
        )

        assert response.status_code == 404
        assert "Service account not found" in response.json()["detail"]

    def test_update_service_account_success(self, client_with_system_admin, db):
        """Test updating a service account successfully."""
        # Create a real service account first
        service = ServiceAccountService(db)
        service_account_data = ServiceAccountCreate(
            name="Update Test Account",
            description="Test account for update operation",
            external_id="ext_update_123",
        )
        system_admin_user = client_with_system_admin.app.state.test_user

        created_account = service.create_service_account(
            service_account_data, created_by=system_admin_user.id
        )

        # Update the service account via API
        update_data = {
            "name": "Updated Name",
            "description": "Updated Description",
        }

        response = client_with_system_admin.put(
            f"/service-accounts/{created_account.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated Description"

    def test_delete_service_account_success(self, client_with_system_admin, db):
        """Test deleting a service account successfully."""
        # Create a real service account first
        service = ServiceAccountService(db)
        service_account_data = ServiceAccountCreate(
            name="Delete Test Account",
            description="Test account for delete operation",
            external_id="ext_delete_123",
        )
        system_admin_user = client_with_system_admin.app.state.test_user

        created_account = service.create_service_account(
            service_account_data, created_by=system_admin_user.id
        )

        # Delete the service account via API
        response = client_with_system_admin.delete(
            f"/service-accounts/{created_account.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]

    def test_regenerate_api_key_success(self, client_with_system_admin, db):
        """Test regenerating API key successfully."""
        # Create a real service account first
        service = ServiceAccountService(db)
        service_account_data = ServiceAccountCreate(
            name="Regenerate Test Account",
            description="Test account for regenerate operation",
            external_id="ext_regenerate_123",
        )
        system_admin_user = client_with_system_admin.app.state.test_user

        created_account = service.create_service_account(
            service_account_data, created_by=system_admin_user.id
        )

        # Store the original API key
        original_api_key = created_account.api_key

        # Regenerate the API key via API
        response = client_with_system_admin.post(
            f"/service-accounts/{created_account.id}/regenerate-key"
        )

        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert data["api_key"] != original_api_key  # Should be different

    def test_assign_role_to_service_account_success(self, client_with_system_admin, db):
        """Test assigning a role to a service account successfully."""
        # Create a real service account first
        service = ServiceAccountService(db)
        service_account_data = ServiceAccountCreate(
            name="Role Test Account",
            description="Test account for role assignment",
            external_id="ext_role_123",
        )
        system_admin_user = client_with_system_admin.app.state.test_user

        created_account = service.create_service_account(
            service_account_data, created_by=system_admin_user.id
        )

        # Assign a role via API
        role_data = {
            "user_id": str(created_account.id),
            "role": "admin",
            "domain": "production",
            "resource": "users",
        }

        response = client_with_system_admin.post(
            f"/service-accounts/{created_account.id}/assign-role",
            json=role_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "successfully assigned" in data["message"]

    def test_get_service_account_roles_success(self, client_with_system_admin, db):
        """Test getting roles for a service account successfully."""
        # Create a real service account first
        service = ServiceAccountService(db)
        service_account_data = ServiceAccountCreate(
            name="Roles Test Account",
            description="Test account for roles retrieval",
            external_id="ext_roles_123",
        )
        system_admin_user = client_with_system_admin.app.state.test_user

        created_account = service.create_service_account(
            service_account_data, created_by=system_admin_user.id
        )

        # Assign a role first
        service.assign_role(created_account.id, "admin", "production")

        # Get roles via API
        response = client_with_system_admin.get(
            f"/service-accounts/{created_account.id}/roles"
        )

        assert response.status_code == 200
        data = response.json()
        assert "roles" in data
        assert "roles_count" in data
        assert data["roles_count"] >= 0

    def test_search_service_accounts_success(self, client_with_system_admin, db):
        """Test searching service accounts successfully."""
        # Create a real service account first
        service = ServiceAccountService(db)
        service_account_data = ServiceAccountCreate(
            name="Search Test Account",
            description="Test account for search operation",
            external_id="ext_search_123",
        )
        system_admin_user = client_with_system_admin.app.state.test_user

        created_account = service.create_service_account(
            service_account_data, created_by=system_admin_user.id
        )

        # Search via API
        response = client_with_system_admin.get("/service-accounts/search?name=Search")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Check if our created account is in the results
        account_names = [account["name"] for account in data]
        assert "Search Test Account" in account_names

    def test_activate_service_account_success(self, client_with_system_admin, db):
        """Test activating a service account successfully."""
        # Create a real service account first
        service = ServiceAccountService(db)
        service_account_data = ServiceAccountCreate(
            name="Activate Test Account",
            description="Test account for activate operation",
            external_id="ext_activate_123",
        )
        system_admin_user = client_with_system_admin.app.state.test_user

        created_account = service.create_service_account(
            service_account_data, created_by=system_admin_user.id
        )

        # Deactivate it first
        service.deactivate_service_account(created_account.id)

        # Activate via API
        response = client_with_system_admin.post(
            f"/service-accounts/{created_account.id}/activate"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    def test_deactivate_service_account_success(self, client_with_system_admin, db):
        """Test deactivating a service account successfully."""
        # Create a real service account first
        service = ServiceAccountService(db)
        service_account_data = ServiceAccountCreate(
            name="Deactivate Test Account",
            description="Test account for deactivate operation",
            external_id="ext_deactivate_123",
        )
        system_admin_user = client_with_system_admin.app.state.test_user

        created_account = service.create_service_account(
            service_account_data, created_by=system_admin_user.id
        )

        # Deactivate via API
        response = client_with_system_admin.post(
            f"/service-accounts/{created_account.id}/deactivate"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    def test_system_admin_authorization_real_casbin(self, client_with_system_admin, db):
        """Test that super admin authorization works with real Casbin."""
        # This test verifies that the real Casbin service recognizes our super admin user
        system_admin_user = client_with_system_admin.app.state.test_user

        # Check that the user has super admin role in Casbin (with domain "*")
        user_roles = casbin_service.get_user_roles(
            str(system_admin_user.id), domain="*"
        )
        assert "system_admin" in user_roles

        # Test that the user can access a protected endpoint
        response = client_with_system_admin.get("/service-accounts/")
        assert response.status_code == 200

    def test_regular_user_authorization_real_casbin(self, client_with_regular_user, db):
        """Test that regular users are properly denied access."""
        regular_user = client_with_regular_user.app.state.test_user

        # Check that the user does NOT have super admin role
        user_roles = casbin_service.get_user_roles(str(regular_user.id), domain="*")
        assert "system_admin" not in user_roles
        assert "user" in user_roles

        # Test that the user is denied access to protected endpoints
        response = client_with_regular_user.get("/service-accounts/")
        assert response.status_code == 403
        assert "Super admin privileges required" in response.json()["detail"]

    def test_service_account_authentication_success(
        self, client, system_admin_service_account, db
    ):
        """Test that service accounts can authenticate using X-Service-Token header."""
        # Get the ORM model from the database
        from app.models.service_account import ServiceAccount

        db_account = (
            db.query(ServiceAccount)
            .filter(ServiceAccount.id == system_admin_service_account.id)
            .first()
        )

        # Ensure the service account has the system_admin role in this session
        casbin_service.assign_role(
            user_id=str(db_account.id), role="system_admin", domain="*"
        )

        # Verify the service account has the system_admin role
        service_account_roles = casbin_service.get_user_roles(str(db_account.id))
        print(f"Service account roles: {service_account_roles}")

        # Set the service account in the app state for the mock middleware
        client.app.state.test_service_account = db_account

        # Use the API key from the created service account
        api_key = system_admin_service_account.api_key

        response = client.get(
            "/service-accounts/", headers={"X-Service-Token": api_key}
        )

        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_service_account_authentication_invalid_token(self, client):
        """Test that invalid service account tokens are rejected."""
        response = client.get(
            "/service-accounts/", headers={"X-Service-Token": "invalid_token"}
        )

        assert response.status_code == 401
        assert "Invalid service token" in response.json()["error"]

    def test_service_account_authentication_inactive_account(self, client, db):
        """Test that inactive service accounts cannot authenticate."""
        service = ServiceAccountService(db)

        # Create an inactive service account
        service_account_data = ServiceAccountCreate(
            name="Inactive Service Account",
            description="An inactive service account",
            is_active=False,
        )

        created_account = service.create_service_account(
            service_account_data, created_by=None
        )

        # Get the ORM model from the database
        from app.models.service_account import ServiceAccount

        db_account = (
            db.query(ServiceAccount)
            .filter(ServiceAccount.id == created_account.id)
            .first()
        )

        # Set the service account in the app state for the mock middleware
        client.app.state.test_service_account = db_account

        response = client.get(
            "/service-accounts/", headers={"X-Service-Token": created_account.api_key}
        )

        assert response.status_code == 410
        assert "Service account is inactive" in response.json()["error"]

    def test_service_account_authentication_expired_account(self, client, db):
        """Test that expired service accounts cannot authenticate."""
        service = ServiceAccountService(db)

        # Create an expired service account
        service_account_data = ServiceAccountCreate(
            name="Expired Service Account",
            description="An expired service account",
            is_active=True,
            expires_at=datetime.now(timezone.utc)
            - timedelta(days=1),  # Expired yesterday
        )

        created_account = service.create_service_account(
            service_account_data, created_by=None
        )

        # Get the ORM model from the database
        from app.models.service_account import ServiceAccount

        db_account = (
            db.query(ServiceAccount)
            .filter(ServiceAccount.id == created_account.id)
            .first()
        )

        # Set the service account in the app state for the mock middleware
        client.app.state.test_service_account = db_account

        response = client.get(
            "/service-accounts/", headers={"X-Service-Token": created_account.api_key}
        )

        assert response.status_code == 410
        assert "Service account has expired" in response.json()["error"]
