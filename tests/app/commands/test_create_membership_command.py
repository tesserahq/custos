from unittest.mock import Mock, patch
from uuid import UUID
from app.commands.memberships.create_membership_command import CreateMembershipCommand
from app.services.membership_service import MembershipService


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
            response = command.execute(
                role=setup_role,
                user_id=user_id,
            )

            # Assertions
            assert response.success is True
            assert response.user_id == user_id
            assert response.role == str(setup_role.identifier)
            assert response.domain is None
            assert response.resource is None
            assert "successfully assigned" in response.message.lower()

            # Verify membership was created
            membership_service = MembershipService(db)
            membership = membership_service.get_membership_by_user_and_role(
                setup_user.id, setup_role.id
            )
            assert membership is not None
            assert membership.user_id == setup_user.id
            assert membership.role_id == setup_role.id

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
            response = command.execute(
                role=setup_role,
                user_id=user_id,
                domain=domain,
                resource=resource,
            )

            # Assertions
            assert response.success is True
            assert response.domain == domain
            assert response.resource == resource

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
            response = command.execute(role=setup_role, user_id=user_id)

            # Should still succeed
            assert response.success is True

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
            response = command.execute(role=setup_role, user_id=user_id)

            # Verify event was published
            assert response.success is True
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
            response = command.execute(role=setup_role, user_id=user_id)

            # Assertions
            assert response.success is True
            assert response.user_id == user_id

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
            response = command.execute(role=setup_role, user_id=user_id)

            assert response.success is True

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
            response1 = command.execute(role=role1, user_id=user_id)
            response2 = command.execute(role=role2, user_id=user_id)

            # Both should succeed
            assert response1.success is True
            assert response2.success is True

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
            response = command.execute(role=setup_role, user_id=user_id)

            # Assertions
            assert response.success is True
            assert response.user_id == user_id

    def test_execute_with_uuid_object(self, db, setup_role, setup_user):
        """Test that command correctly handles UUID object passed as user_id (simulating router behavior)."""
        # Pass UUID object directly (as router does when converting string to UUID)
        user_id_uuid = setup_user.id

        command = CreateMembershipCommand(db, nats_publisher=None)
        # Mock the assign_role method
        with patch.object(
            command.casbin_service, "assign_role", return_value=True
        ) as mock_assign_role:
            response = command.execute(
                role=setup_role,
                user_id=user_id_uuid,  # Pass UUID object, not string
            )

            # Assertions - user_id in response should be a string (converted from UUID)
            assert response.success is True
            assert isinstance(
                response.user_id, str
            ), "user_id should be converted to string"
            assert response.user_id == str(user_id_uuid)
            assert response.role == str(setup_role.identifier)
            assert "successfully assigned" in response.message.lower()

            # Verify Casbin was called with string (UUID converted to string)
            mock_assign_role.assert_called_once_with(
                user_id=str(user_id_uuid),  # Command converts UUID to string for casbin
                role=str(setup_role.identifier),
                domain=None,
                resource=None,
            )
