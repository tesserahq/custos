from unittest.mock import Mock, patch
from uuid import UUID
from app.commands.memberships.create_membership_command import CreateMembershipCommand
from app.services.membership_service import MembershipService
from app.models.membership import Membership as MembershipModel


class TestCreateMembershipCommand:
    """Test cases for CreateMembershipCommand."""

    def test_execute_success(self, db, setup_role, setup_user):
        """Test successful role binding creation with membership."""
        user_id = str(setup_user.id)

        command = CreateMembershipCommand(db, nats_publisher=None)
        # Mock the assign_role method
        with patch.object(
            command.casbin_service, "assign_role", return_value=True
        ) as mock_assign_role:
            membership = command.execute(
                role=setup_role,
                user_id=user_id,
            )

            # Assertions - should return Membership model object
            assert isinstance(membership, MembershipModel)
            assert membership.user_id == setup_user.id
            assert membership.role_id == setup_role.id
            assert membership.domain is None
            assert membership.id is not None
            assert membership.created_at is not None
            assert membership.updated_at is not None

            # Verify membership was created in database
            membership_service = MembershipService(db)
            db_membership = membership_service.get_membership_by_user_and_role(
                setup_user.id, setup_role.id
            )
            assert db_membership is not None
            assert db_membership.user_id == setup_user.id
            assert db_membership.role_id == setup_role.id

            # Verify Casbin was called
            mock_assign_role.assert_called_once_with(
                user_id=user_id,
                role=str(setup_role.identifier),
                domain=None,
                resource=None,
            )

    def test_execute_success_with_domain_and_resource(
        self, db, setup_role, setup_user, faker
    ):
        """Test successful role binding with domain and resource."""
        user_id = str(setup_user.id)
        domain = faker.word().lower()
        resource = faker.word().lower()

        command = CreateMembershipCommand(db, nats_publisher=None)
        # Mock the assign_role method
        with patch.object(
            command.casbin_service, "assign_role", return_value=True
        ) as mock_assign_role:
            membership = command.execute(
                role=setup_role,
                user_id=user_id,
                domain=domain,
                resource=resource,
            )

            # Assertions
            assert isinstance(membership, MembershipModel)
            assert membership.domain == domain
            assert membership.user_id == setup_user.id
            assert membership.role_id == setup_role.id

            # Verify Casbin was called with domain and resource
            mock_assign_role.assert_called_once_with(
                user_id=user_id,
                role=str(setup_role.identifier),
                domain=domain,
                resource=resource,
            )

    def test_execute_membership_already_exists(self, db, setup_role, setup_user):
        """Test that existing membership is handled gracefully."""
        user_id = str(setup_user.id)

        # Create existing membership
        membership_service = MembershipService(db)
        from app.schemas.membership import MembershipCreate

        existing_membership = membership_service.create_membership(
            MembershipCreate(user_id=setup_user.id, role_id=setup_role.id)
        )

        command = CreateMembershipCommand(db, nats_publisher=None)
        # Mock the assign_role method
        with patch.object(command.casbin_service, "assign_role", return_value=True):
            membership = command.execute(role=setup_role, user_id=user_id)

            # Should still succeed and return the existing membership
            assert isinstance(membership, MembershipModel)
            assert membership.id == existing_membership.id
            assert membership.user_id == setup_user.id
            assert membership.role_id == setup_role.id

            # Verify only one membership exists (not duplicated)
            memberships = membership_service.get_memberships_by_user(setup_user.id)
            assert len(memberships) == 1
            assert memberships[0].id == existing_membership.id

    def test_execute_publishes_event(self, db, setup_role, setup_user):
        """Test that bind creation publishes an event when nats_publisher is provided."""
        user_id = str(setup_user.id)

        # Mock the nats_publisher
        mock_publisher = Mock()
        mock_publisher.publish_sync = Mock()

        command = CreateMembershipCommand(db, nats_publisher=mock_publisher)
        # Mock the assign_role method
        with patch.object(command.casbin_service, "assign_role", return_value=True):
            membership = command.execute(role=setup_role, user_id=user_id)

            # Verify membership was returned
            assert isinstance(membership, MembershipModel)
            # Verify event was published
            assert mock_publisher.publish_sync.called
            call_args = mock_publisher.publish_sync.call_args
            assert call_args is not None
            # Verify the event_type was passed
            assert len(call_args[0]) == 2  # event and event_type

    def test_execute_without_publisher(self, db, setup_role, setup_user):
        """Test that bind creation works without nats_publisher."""
        user_id = str(setup_user.id)

        command = CreateMembershipCommand(db, nats_publisher=None)
        # Mock the assign_role method
        with patch.object(command.casbin_service, "assign_role", return_value=True):
            membership = command.execute(role=setup_role, user_id=user_id)

            # Assertions
            assert isinstance(membership, MembershipModel)
            assert membership.user_id == setup_user.id
            assert membership.role_id == setup_role.id

    def test_execute_event_publishing_failure_does_not_raise(
        self, db, setup_role, setup_user
    ):
        """Test that event publishing failure doesn't raise an exception."""
        user_id = str(setup_user.id)

        # Mock the nats_publisher to raise an exception
        mock_publisher = Mock()
        mock_publisher.publish_sync = Mock(side_effect=Exception("NATS error"))

        command = CreateMembershipCommand(db, nats_publisher=mock_publisher)
        # Mock the assign_role method
        with patch.object(command.casbin_service, "assign_role", return_value=True):
            # Should still succeed even if event publishing fails
            membership = command.execute(role=setup_role, user_id=user_id)

            assert isinstance(membership, MembershipModel)
            assert membership.user_id == setup_user.id

    def test_execute_multiple_bindings_same_user_different_roles(
        self, db, setup_user, faker
    ):
        """Test creating multiple bindings for the same user with different roles."""
        user_id = str(setup_user.id)

        # Create two roles
        from app.models.role import Role

        role1 = Role(
            name=faker.word().capitalize() + "Role1",
            identifier=faker.uuid4(),
        )
        role2 = Role(
            name=faker.word().capitalize() + "Role2",
            identifier=faker.uuid4(),
        )
        db.add(role1)
        db.add(role2)
        db.commit()
        db.refresh(role1)
        db.refresh(role2)

        command = CreateMembershipCommand(db, nats_publisher=None)
        # Mock the assign_role method
        with patch.object(command.casbin_service, "assign_role", return_value=True):
            # Create bindings for both roles
            membership1 = command.execute(role=role1, user_id=user_id)
            membership2 = command.execute(role=role2, user_id=user_id)

            # Both should succeed
            assert isinstance(membership1, MembershipModel)
            assert isinstance(membership2, MembershipModel)
            assert membership1.role_id == role1.id
            assert membership2.role_id == role2.id

            # Verify both memberships exist
            membership_service = MembershipService(db)
            memberships = membership_service.get_memberships_by_user(setup_user.id)
            assert len(memberships) == 2
            role_ids = {m.role_id for m in memberships}
            assert role1.id in role_ids
            assert role2.id in role_ids

    def test_execute_with_default_publisher(self, db, setup_role, setup_user):
        """Test that command works with default NatsEventPublisher."""
        user_id = str(setup_user.id)

        # Don't pass nats_publisher, should create default
        command = CreateMembershipCommand(db)
        # Mock the assign_role method
        with patch.object(command.casbin_service, "assign_role", return_value=True):
            membership = command.execute(role=setup_role, user_id=user_id)

            # Assertions
            assert isinstance(membership, MembershipModel)
            assert membership.user_id == setup_user.id
            assert membership.role_id == setup_role.id

    def test_execute_with_uuid_object(self, db, setup_role, setup_user):
        """Test that command correctly handles UUID object passed as user_id (simulating router behavior)."""
        # Pass UUID object directly (as router does when converting string to UUID)
        user_id_uuid = setup_user.id

        command = CreateMembershipCommand(db, nats_publisher=None)
        # Mock the assign_role method
        with patch.object(
            command.casbin_service, "assign_role", return_value=True
        ) as mock_assign_role:
            membership = command.execute(
                role=setup_role,
                user_id=user_id_uuid,  # Pass UUID object, not string
            )

            # Assertions - should return Membership model object
            assert isinstance(membership, MembershipModel)
            assert membership.user_id == user_id_uuid
            assert membership.role_id == setup_role.id
            assert membership.id is not None
            assert membership.created_at is not None

            # Verify Casbin was called with string (UUID converted to string)
            mock_assign_role.assert_called_once_with(
                user_id=str(user_id_uuid),  # Command converts UUID to string for casbin
                role=str(setup_role.identifier),
                domain=None,
                resource=None,
            )
