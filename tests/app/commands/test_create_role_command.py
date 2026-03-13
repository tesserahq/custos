import pytest
from unittest.mock import Mock, patch
from app.commands.role.create_role_command import CreateRoleCommand
from app.schemas.role import RoleCreate


class TestCreateRoleCommand:
    """Test cases for CreateRoleCommand."""

    def test_execute_success(self, db, faker):
        """Test successful role creation."""
        role_data = RoleCreate(
            name=faker.word().capitalize() + "Role",
            identifier=faker.uuid4(),
            description=faker.text(100),
        )

        command = CreateRoleCommand(db, nats_publisher=None)
        role = command.execute(role_data)

        # Assertions
        assert role.id is not None
        assert role.name == role_data.name
        assert role.description == role_data.description
        assert role.created_at is not None
        assert role.updated_at is not None

    def test_execute_duplicate_name(self, db, setup_role, faker):
        """Test that creating a role with duplicate name raises ValueError."""
        role_data = RoleCreate(
            name=setup_role.name,  # Use existing role name
            identifier=setup_role.identifier,
            description=faker.text(100),
        )

        command = CreateRoleCommand(db, nats_publisher=None)

        with pytest.raises(ValueError) as exc_info:
            command.execute(role_data)

        assert "already exists" in str(exc_info.value).lower()

    def test_execute_publishes_event(self, db, faker):
        """Test that role creation publishes an event when nats_publisher is provided."""
        role_data = RoleCreate(
            name=faker.word().capitalize() + "Role",
            identifier=faker.uuid4(),
            description=faker.text(100),
        )

        # Mock the nats_publisher
        mock_publisher = Mock()
        mock_publisher.publish_sync = Mock()

        command = CreateRoleCommand(db, nats_publisher=mock_publisher)
        command.execute(role_data)

        # Verify event was published
        assert mock_publisher.publish_sync.called
        call_args = mock_publisher.publish_sync.call_args
        assert call_args is not None
        # Verify the event_type was passed
        assert len(call_args[0]) == 2  # event and event_type

    def test_execute_without_publisher(self, db, faker):
        """Test that role creation works without nats_publisher."""
        role_data = RoleCreate(
            name=faker.word().capitalize() + "Role",
            identifier=faker.uuid4(),
            description=faker.text(100),
        )

        command = CreateRoleCommand(db, nats_publisher=None)
        role = command.execute(role_data)

        # Assertions
        assert role.id is not None
        assert role.name == role_data.name

    def test_execute_rollback_on_error(self, db, faker):
        """Test that exceptions are properly handled and error message is set."""
        role_data = RoleCreate(
            name=faker.word().capitalize() + "Role",
            identifier=faker.uuid4(),
            description=faker.text(100),
        )

        command = CreateRoleCommand(db, nats_publisher=None)

        # Mock the service to raise an exception
        with patch.object(
            command.role_repository,
            "create_role",
            side_effect=Exception("Database error"),
        ):
            with pytest.raises(Exception) as exc_info:
                command.execute(role_data)

            assert "Failed to create role" in str(exc_info.value)

    def test_execute_value_error_not_rolled_back(self, db, setup_role, faker):
        """Test that ValueError exceptions allow the transaction to continue."""
        role_data = RoleCreate(
            name=setup_role.name,  # Duplicate name
            identifier=setup_role.identifier,
            description=faker.text(100),
        )

        command = CreateRoleCommand(db, nats_publisher=None)

        with pytest.raises(ValueError) as exc_info:
            command.execute(role_data)

        assert "already exists" in str(exc_info.value).lower()
        # Verify the existing role is still there (transaction wasn't rolled back)
        from app.repositories.role_repository import RoleRepository

        existing_role = RoleRepository(db).get_role(setup_role.id)
        assert existing_role is not None

    def test_execute_event_publishing_failure_does_not_raise(self, db, faker):
        """Test that event publishing failure doesn't raise an exception."""
        role_data = RoleCreate(
            name=faker.word().capitalize() + "Role",
            identifier=faker.uuid4(),
            description=faker.text(100),
        )

        # Mock the nats_publisher to raise an exception
        mock_publisher = Mock()
        mock_publisher.publish_sync = Mock(side_effect=Exception("NATS error"))

        command = CreateRoleCommand(db, nats_publisher=mock_publisher)

        # Should still succeed even if event publishing fails
        role = command.execute(role_data)

        assert role.id is not None
        assert role.name == role_data.name

    def test_execute_with_default_publisher(self, db, faker):
        """Test that command works with default NatsEventPublisher."""
        role_data = RoleCreate(
            name=faker.word().capitalize() + "Role",
            identifier=faker.uuid4(),
            description=faker.text(100),
        )

        # Don't pass nats_publisher, should create default
        command = CreateRoleCommand(db)
        role = command.execute(role_data)

        # Assertions
        assert role.id is not None
        assert role.name == role_data.name

    def test_execute_role_without_description(self, db, faker):
        """Test creating a role without description."""
        role_data = RoleCreate(
            name=faker.word().capitalize() + "Role",
            identifier=faker.uuid4(),
        )

        command = CreateRoleCommand(db, nats_publisher=None)
        role = command.execute(role_data)

        # Assertions
        assert role.id is not None
        assert role.name == role_data.name
        assert role.description is None

    def test_execute_multiple_roles_different_names(self, db, faker):
        """Test creating multiple roles with different names."""
        role_data1 = RoleCreate(
            name=faker.word().capitalize() + "Role1",
            identifier=faker.uuid4(),
            description=faker.text(100),
        )
        role_data2 = RoleCreate(
            name=faker.word().capitalize() + "Role2",
            identifier=faker.uuid4(),
            description=faker.text(100),
        )

        command = CreateRoleCommand(db, nats_publisher=None)

        role1 = command.execute(role_data1)
        role2 = command.execute(role_data2)

        # Assertions
        assert role1.id != role2.id
        assert role1.name != role2.name
