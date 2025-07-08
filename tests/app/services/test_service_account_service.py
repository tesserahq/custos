import pytest
from uuid import UUID
from datetime import datetime, timezone, timedelta
from app.services.service_account_service import ServiceAccountService
from app.schemas.service_account import ServiceAccountCreate, ServiceAccountUpdate
from app.models.service_account import ServiceAccount


class TestServiceAccountService:
    """Test cases for ServiceAccountService."""

    def test_create_service_account(self, db):
        """Test creating a service account."""
        service = ServiceAccountService(db)

        # Create service account data
        service_account_data = ServiceAccountCreate(
            name="Test Service Account",
            description="A test service account",
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )

        # Create the service account
        service_account = service.create_service_account(service_account_data)

        # Verify the service account was created
        assert service_account.id is not None
        assert service_account.name == "Test Service Account"
        assert service_account.description == "A test service account"
        assert service_account.is_active is True
        assert service_account.api_key is not None
        assert service_account.api_key.startswith("sk_")
        assert service_account.api_key_hash is not None

    def test_get_service_account_by_id(self, db):
        """Test retrieving a service account by ID."""
        service = ServiceAccountService(db)

        # Create a service account
        service_account_data = ServiceAccountCreate(name="Test Account")
        created_account = service.create_service_account(service_account_data)

        # Retrieve by ID
        retrieved_account = service.get_service_account(created_account.id)

        assert retrieved_account is not None
        assert retrieved_account.id == created_account.id
        assert retrieved_account.name == "Test Account"

    def test_get_service_account_by_api_key(self, db):
        """Test retrieving a service account by API key."""
        service = ServiceAccountService(db)

        # Create a service account
        service_account_data = ServiceAccountCreate(name="Test Account")
        created_account = service.create_service_account(service_account_data)
        api_key = created_account.api_key

        # Retrieve by API key
        retrieved_account = service.get_service_account_by_api_key(api_key)

        assert retrieved_account is not None
        assert retrieved_account.id == created_account.id

    def test_update_service_account(self, db):
        """Test updating a service account."""
        service = ServiceAccountService(db)

        # Create a service account
        service_account_data = ServiceAccountCreate(name="Original Name")
        created_account = service.create_service_account(service_account_data)

        # Update the service account
        update_data = ServiceAccountUpdate(
            name="Updated Name", description="Updated description"
        )
        updated_account = service.update_service_account(
            created_account.id, update_data
        )

        assert updated_account is not None
        assert updated_account.name == "Updated Name"
        assert updated_account.description == "Updated description"

    def test_regenerate_api_key(self, db):
        """Test regenerating an API key."""
        service = ServiceAccountService(db)

        # Create a service account
        service_account_data = ServiceAccountCreate(name="Test Account")
        created_account = service.create_service_account(service_account_data)
        original_api_key = created_account.api_key

        # Regenerate the API key
        new_account = service.regenerate_api_key(created_account.id)

        assert new_account is not None
        assert new_account.api_key != original_api_key
        assert new_account.api_key.startswith("sk_")

    def test_deactivate_and_activate_service_account(self, db):
        """Test deactivating and activating a service account."""
        service = ServiceAccountService(db)

        # Create a service account
        service_account_data = ServiceAccountCreate(name="Test Account")
        created_account = service.create_service_account(service_account_data)

        # Deactivate
        deactivated_account = service.deactivate_service_account(created_account.id)
        assert deactivated_account.is_active is False

        # Activate
        activated_account = service.activate_service_account(created_account.id)
        assert activated_account.is_active is True

    def test_update_last_used(self, db):
        """Test updating the last used timestamp."""
        service = ServiceAccountService(db)

        # Create a service account
        service_account_data = ServiceAccountCreate(name="Test Account")
        created_account = service.create_service_account(service_account_data)

        # Update last used
        updated_account = service.update_last_used(created_account.id)
        assert updated_account.last_used_at is not None

    def test_is_expired(self, db):
        """Test checking if a service account is expired."""
        service = ServiceAccountService(db)

        # Create an expired service account
        expired_date = datetime.now(timezone.utc) - timedelta(days=1)
        service_account_data = ServiceAccountCreate(
            name="Expired Account", expires_at=expired_date
        )
        expired_account_schema = service.create_service_account(service_account_data)

        # Get the actual model instance to test the methods
        expired_account_model = service.get_service_account(expired_account_schema.id)

        # Test the model method
        assert expired_account_model.is_expired() is True
        assert expired_account_model.can_be_used() is False

    def test_can_be_used(self, db):
        """Test checking if a service account can be used."""
        service = ServiceAccountService(db)

        # Create a valid service account
        future_date = datetime.now(timezone.utc) + timedelta(days=30)
        service_account_data = ServiceAccountCreate(
            name="Valid Account", expires_at=future_date, is_active=True
        )
        valid_account_schema = service.create_service_account(service_account_data)

        # Get the actual model instance to test the methods
        valid_account_model = service.get_service_account(valid_account_schema.id)

        # Test the model method
        assert valid_account_model.is_expired() is False
        assert valid_account_model.can_be_used() is True

    def test_delete_service_account(self, db):
        """Test deleting a service account."""
        service = ServiceAccountService(db)

        # Create a service account
        service_account_data = ServiceAccountCreate(name="Test Account")
        created_account = service.create_service_account(service_account_data)

        # Delete the service account
        result = service.delete_service_account(created_account.id)
        assert result is True

        # Verify it's deleted
        retrieved_account = service.get_service_account(created_account.id)
        assert retrieved_account is None

    def test_search_service_accounts(self, db):
        """Test searching service accounts."""
        service = ServiceAccountService(db)

        # Create multiple service accounts
        service.create_service_account(ServiceAccountCreate(name="Account One"))
        service.create_service_account(ServiceAccountCreate(name="Account Two"))
        service.create_service_account(ServiceAccountCreate(name="Another Account"))

        # Search by name
        results = service.search({"name": {"operator": "ilike", "value": "%Account%"}})
        assert len(results) == 3

        # Search by exact name
        results = service.search({"name": "Account One"})
        assert len(results) == 1
        assert results[0].name == "Account One"

    def test_get_active_service_accounts(self, db):
        """Test getting active service accounts."""
        service = ServiceAccountService(db)

        # Create active and inactive accounts
        service.create_service_account(
            ServiceAccountCreate(name="Active 1", is_active=True)
        )
        service.create_service_account(
            ServiceAccountCreate(name="Active 2", is_active=True)
        )
        service.create_service_account(
            ServiceAccountCreate(name="Inactive", is_active=False)
        )

        # Get active accounts
        active_accounts = service.get_active_service_accounts()
        assert len(active_accounts) == 2
        assert all(account.is_active for account in active_accounts)

    def test_get_expired_service_accounts(self, db):
        """Test getting expired service accounts."""
        service = ServiceAccountService(db)

        # Create expired and non-expired accounts
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        future_date = datetime.now(timezone.utc) + timedelta(days=30)

        service.create_service_account(
            ServiceAccountCreate(name="Expired 1", expires_at=past_date)
        )
        service.create_service_account(
            ServiceAccountCreate(name="Expired 2", expires_at=past_date)
        )
        service.create_service_account(
            ServiceAccountCreate(name="Valid", expires_at=future_date)
        )
        service.create_service_account(ServiceAccountCreate(name="No Expiry"))

        # Get expired accounts
        expired_accounts = service.get_expired_service_accounts()
        assert len(expired_accounts) == 2
        assert all(account.is_expired() for account in expired_accounts)
