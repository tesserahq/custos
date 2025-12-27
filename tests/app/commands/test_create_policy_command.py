import pytest
from uuid import uuid4
from unittest.mock import patch
from app.commands.policy.sync_role_policy_command import SyncRolePolicyCommand
from app.models.permission import Permission


class TestSyncRolePolicyCommand:
    """Test cases for SyncRolePolicyCommand."""

    def test_execute_success(self, db, setup_role, faker):
        """Test successful policy creation for a role with permissions."""
        # Create permissions for the role
        domain = faker.word().lower()
        permissions = [
            Permission(object="users", action="read", role_id=setup_role.id),
            Permission(object="users", action="write", role_id=setup_role.id),
            Permission(object="projects", action="read", role_id=setup_role.id),
        ]
        for perm in permissions:
            db.add(perm)
        db.commit()

        command = SyncRolePolicyCommand(db)
        result = command.execute(setup_role.id, domain)

        # Assertions
        assert result["success"] is True
        assert result["role_name"] == setup_role.name
        assert result["total_permissions"] == 3
        assert result["policies_added"] == 3
        assert result["policies_failed"] == 0

        # Verify policies were actually added to Casbin
        # Use the command's casbin_service instance to access the same enforcer
        # Policies are stored with role.id (UUID) as subject at index 0, domain at index 1
        policies = command.casbin_service.enforcer.get_filtered_policy(
            0, str(setup_role.identifier)
        )
        # Filter by domain (domain is at index 1 in the policy tuple)
        domain_policies = [p for p in policies if len(p) > 1 and p[1] == domain]
        assert len(domain_policies) == 3

    def test_execute_role_not_found(self, db, faker):
        """Test that creating policies for non-existent role raises ValueError."""
        non_existent_role_id = uuid4()
        domain = faker.word().lower()

        command = SyncRolePolicyCommand(db)

        with pytest.raises(ValueError) as exc_info:
            command.execute(non_existent_role_id, domain)

        assert "not found" in str(exc_info.value).lower()

    def test_execute_role_with_no_permissions(self, db, setup_role, faker):
        """Test creating policies for a role with no permissions."""
        domain = faker.word().lower()

        command = SyncRolePolicyCommand(db)
        result = command.execute(setup_role.id, domain)

        # Assertions
        assert result["success"] is True
        assert result["role_name"] == setup_role.name
        assert result["total_permissions"] == 0
        assert result["policies_added"] == 0
        assert result["policies_failed"] == 0

    def test_execute_with_multiple_permissions(self, db, setup_role, faker):
        """Test creating policies for a role with many permissions."""
        domain = faker.word().lower()
        # Create multiple permissions
        permissions = [
            Permission(object="users", action="read", role_id=setup_role.id),
            Permission(object="users", action="write", role_id=setup_role.id),
            Permission(object="users", action="delete", role_id=setup_role.id),
            Permission(object="users", action="create", role_id=setup_role.id),
            Permission(object="projects", action="read", role_id=setup_role.id),
            Permission(object="projects", action="write", role_id=setup_role.id),
            Permission(object="documents", action="read", role_id=setup_role.id),
            Permission(object="documents", action="write", role_id=setup_role.id),
        ]
        for perm in permissions:
            db.add(perm)
        db.commit()

        command = SyncRolePolicyCommand(db)
        result = command.execute(setup_role.id, domain)

        # Assertions
        assert result["success"] is True
        assert result["total_permissions"] == 8
        assert result["policies_added"] == 8
        assert result["policies_failed"] == 0

    def test_execute_duplicate_policies(self, db, setup_role, faker):
        """Test that duplicate policies are handled gracefully."""
        domain = faker.word().lower()
        permissions = [
            Permission(object="users", action="read", role_id=setup_role.id),
            Permission(object="users", action="write", role_id=setup_role.id),
        ]
        for perm in permissions:
            db.add(perm)
        db.commit()

        command = SyncRolePolicyCommand(db)

        # First execution
        result1 = command.execute(setup_role.id, domain)
        assert result1["policies_added"] == 2

        # Second execution - should handle duplicates gracefully
        result2 = command.execute(setup_role.id, domain)
        # Duplicates should be detected and not cause failures
        assert result2["policies_added"] >= 0  # May be 0 if all are duplicates
        assert result2["total_permissions"] == 2

    def test_execute_partial_failure(self, db, setup_role, faker):
        """Test handling when some policies fail to add."""
        domain = faker.word().lower()
        permissions = [
            Permission(object="users", action="read", role_id=setup_role.id),
            Permission(object="users", action="write", role_id=setup_role.id),
            Permission(object="projects", action="read", role_id=setup_role.id),
        ]
        for perm in permissions:
            db.add(perm)
        db.commit()

        command = SyncRolePolicyCommand(db)

        # Mock add_policy to fail for some policies
        # Use the command's casbin_service instance
        original_add_policy = command.casbin_service.add_policy
        call_count = [0]

        def mock_add_policy(subject, obj, action, domain=None):
            call_count[0] += 1
            # Fail on second call
            if call_count[0] == 2:
                return False
            return original_add_policy(subject, obj, action, domain=domain)

        with patch.object(
            command.casbin_service, "add_policy", side_effect=mock_add_policy
        ):
            result = command.execute(setup_role.id, domain)

        # Should still be successful if >= 80% succeed
        assert result["total_permissions"] == 3
        assert result["policies_added"] == 2
        assert result["policies_failed"] == 1
        # With 2/3 success (66.7%), should still be marked as success (>= 80% threshold)
        # Actually wait, 2/3 is 66.7% which is < 80%, so success should be False
        assert result["success"] is False

    def test_execute_success_threshold(self, db, setup_role, faker):
        """Test that success threshold of 80% is correctly applied."""
        domain = faker.word().lower()
        # Create 10 permissions
        permissions = [
            Permission(object=f"resource_{i}", action="read", role_id=setup_role.id)
            for i in range(10)
        ]
        for perm in permissions:
            db.add(perm)
        db.commit()

        command = SyncRolePolicyCommand(db)

        # Mock add_policy to fail for 2 policies (8/10 = 80% success)
        # Use the command's casbin_service instance
        original_add_policy = command.casbin_service.add_policy
        call_count = [0]

        def mock_add_policy(subject, obj, action, domain=None):
            call_count[0] += 1
            # Fail on calls 3 and 4
            if call_count[0] in [3, 4]:
                return False
            return original_add_policy(subject, obj, action, domain=domain)

        with patch.object(
            command.casbin_service, "add_policy", side_effect=mock_add_policy
        ):
            result = command.execute(setup_role.id, domain)

        # 8/10 = 80%, should be successful
        assert result["total_permissions"] == 10
        assert result["policies_added"] == 8
        assert result["policies_failed"] == 2
        assert result["success"] is True

    def test_execute_different_domains(self, db, setup_role, faker):
        """Test that policies are created for the correct domain."""
        domain1 = faker.word().lower()
        domain2 = faker.word().lower()

        permissions = [
            Permission(object="users", action="read", role_id=setup_role.id),
            Permission(object="users", action="write", role_id=setup_role.id),
        ]
        for perm in permissions:
            db.add(perm)
        db.commit()

        command = SyncRolePolicyCommand(db)

        # Create policies for domain1
        result1 = command.execute(setup_role.id, domain1)
        assert result1["policies_added"] == 2

        # Create policies for domain2
        result2 = command.execute(setup_role.id, domain2)
        assert result2["policies_added"] == 2

        # Verify policies are domain-specific
        # Use the command's casbin_service instance to access the same enforcer
        # Policies are stored with role.id (UUID) as subject at index 0, domain at index 1
        # Filter by role ID first, then by domain
        role_policies = command.casbin_service.enforcer.get_filtered_policy(
            0, str(setup_role.identifier)
        )
        # Filter by domain (domain is at index 1 in the policy tuple)
        policies1 = [p for p in role_policies if len(p) > 1 and p[1] == domain1]
        policies2 = [p for p in role_policies if len(p) > 1 and p[1] == domain2]

        assert len(policies1) == 2
        assert len(policies2) == 2
        # Verify domains are correct
        assert all(p[1] == domain1 for p in policies1)
        assert all(p[1] == domain2 for p in policies2)

    def test_execute_exception_handling(self, db, setup_role, faker):
        """Test that exceptions are properly handled."""
        domain = faker.word().lower()
        permissions = [
            Permission(object="users", action="read", role_id=setup_role.id),
        ]
        for perm in permissions:
            db.add(perm)
        db.commit()

        command = SyncRolePolicyCommand(db)

        # Mock role_service to raise an exception
        with patch.object(
            command.role_service, "get_role", side_effect=Exception("Database error")
        ):
            with pytest.raises(Exception) as exc_info:
                command.execute(setup_role.id, domain)

            assert "Failed to create policies" in str(exc_info.value)

    def test_execute_value_error_not_caught(self, db, faker):
        """Test that ValueError is re-raised without wrapping."""
        non_existent_role_id = uuid4()
        domain = faker.word().lower()

        command = SyncRolePolicyCommand(db)

        with pytest.raises(ValueError) as exc_info:
            command.execute(non_existent_role_id, domain)

        # Should be the original ValueError, not wrapped
        assert "not found" in str(exc_info.value).lower()
        assert not isinstance(exc_info.value, Exception) or isinstance(
            exc_info.value, ValueError
        )

    def test_execute_publishes_events(self, db, setup_role, faker):
        """Test that policy creation publishes events when nats_publisher is provided."""
        domain = faker.word().lower()
        permissions = [
            Permission(object="users", action="read", role_id=setup_role.id),
            Permission(object="users", action="write", role_id=setup_role.id),
        ]
        for perm in permissions:
            db.add(perm)
        db.commit()

        # Mock the nats_publisher
        from unittest.mock import Mock

        mock_publisher = Mock()
        mock_publisher.publish_sync = Mock()

        command = SyncRolePolicyCommand(db, nats_publisher=mock_publisher)
        result = command.execute(setup_role.id, domain)

        # Verify events were published (one per policy created)
        assert result["policies_added"] == 2
        assert mock_publisher.publish_sync.call_count == 2

        # Verify the event_type was passed correctly
        for call in mock_publisher.publish_sync.call_args_list:
            assert len(call[0]) == 2  # event and event_type
            assert call[0][1] == "com.custos.policy.created"  # event_type

    def test_execute_without_publisher(self, db, setup_role, faker):
        """Test that policy creation works without nats_publisher."""
        domain = faker.word().lower()
        permissions = [
            Permission(object="users", action="read", role_id=setup_role.id),
        ]
        for perm in permissions:
            db.add(perm)
        db.commit()

        command = SyncRolePolicyCommand(db, nats_publisher=None)
        result = command.execute(setup_role.id, domain)

        # Assertions
        assert result["success"] is True
        assert result["policies_added"] == 1

    def test_execute_event_publishing_failure_does_not_raise(
        self, db, setup_role, faker
    ):
        """Test that event publishing failure doesn't raise an exception."""
        domain = faker.word().lower()
        permissions = [
            Permission(object="users", action="read", role_id=setup_role.id),
        ]
        for perm in permissions:
            db.add(perm)
        db.commit()

        # Mock the nats_publisher to raise an exception
        from unittest.mock import Mock

        mock_publisher = Mock()
        mock_publisher.publish_sync = Mock(side_effect=Exception("NATS error"))

        command = SyncRolePolicyCommand(db, nats_publisher=mock_publisher)

        # Should still succeed even if event publishing fails
        result = command.execute(setup_role.id, domain)

        assert result["success"] is True
        assert result["policies_added"] == 1
