"""Flows are atomic under the managed transaction boundary, Casbin included.

Each test runs a command the way an entry point does (``execution_boundary``:
commit on success, roll back on error). Casbin rules are stored in the
execution's transaction and reach the in-memory enforcer (which answers
authorization checks) only after commit.
"""

from unittest.mock import Mock

import pytest
from casbin_sqlalchemy_adapter import CasbinRule

from app.commands.memberships.create_membership_command import CreateMembershipCommand
from app.commands.memberships.delete_membership_command import DeleteMembershipCommand
from app.commands.role.delete_role_command import DeleteRoleCommand
from app.models.role import Role
from app.repositories.casbin_repository import get_casbin_repository
from app.repositories.membership_repository import MembershipRepository


def _stored_grants(db, user_id, role_identifier, domain):
    return (
        db.query(CasbinRule)
        .filter_by(ptype="g", v0=str(user_id), v1=role_identifier, v2=domain)
        .count()
    )


def test_failed_membership_grants_nothing(
    db, execution_boundary, setup_role, setup_user, faker, monkeypatch
):
    """A failure after the Casbin assignment leaves no membership, no stored
    rule and no effective grant, and publishes nothing."""
    domain = f"tenant-{faker.uuid4()}"
    publisher = Mock()
    command = CreateMembershipCommand(db, nats_publisher=publisher)

    monkeypatch.setattr(
        command.membership_repository,
        "get_membership_by_user_and_role",
        Mock(side_effect=[None, RuntimeError("failure after the Casbin assignment")]),
    )

    with pytest.raises(RuntimeError, match="after the Casbin assignment"):
        with execution_boundary():
            command.execute(role=setup_role, user_id=setup_user.id, domain=domain)

    identifier = str(setup_role.identifier)
    assert _stored_grants(db, setup_user.id, identifier, domain) == 0
    assert identifier not in get_casbin_repository().get_user_roles(
        str(setup_user.id), domain
    )
    assert (
        MembershipRepository(db).get_membership_by_user_and_role(
            setup_user.id, setup_role.id, domain
        )
        is None
    )
    publisher.publish_sync.assert_not_called()


def test_membership_grant_takes_effect_on_commit(
    db, execution_boundary, setup_role, setup_user, faker
):
    domain = f"tenant-{faker.uuid4()}"
    identifier = str(setup_role.identifier)
    casbin = get_casbin_repository()
    publisher = Mock()

    try:
        with execution_boundary():
            CreateMembershipCommand(db, nats_publisher=publisher).execute(
                role=setup_role, user_id=setup_user.id, domain=domain
            )
            # Stored in this transaction, not yet effective or announced.
            assert _stored_grants(db, setup_user.id, identifier, domain) == 1
            assert identifier not in casbin.get_user_roles(str(setup_user.id), domain)
            publisher.publish_sync.assert_not_called()

        assert identifier in casbin.get_user_roles(str(setup_user.id), domain)
        publisher.publish_sync.assert_called_once()
    finally:
        # The enforcer is process-wide; the db fixture only undoes the rows.
        casbin.enforcer.remove_grouping_policy(str(setup_user.id), identifier, domain)


def test_failed_revocation_keeps_the_grant(
    db, execution_boundary, setup_role, setup_user, faker, monkeypatch
):
    domain = f"tenant-{faker.uuid4()}"
    identifier = str(setup_role.identifier)
    casbin = get_casbin_repository()

    try:
        with execution_boundary():
            CreateMembershipCommand(db, nats_publisher=None).execute(
                role=setup_role, user_id=setup_user.id, domain=domain
            )

        command = DeleteMembershipCommand(db, nats_publisher=None)
        monkeypatch.setattr(
            command.membership_repository,
            "delete_membership_by_user_and_role",
            Mock(side_effect=RuntimeError("membership delete failed")),
        )

        with pytest.raises(RuntimeError, match="membership delete failed"):
            with execution_boundary():
                command.execute(role=setup_role, user_id=setup_user.id, domain=domain)

        assert _stored_grants(db, setup_user.id, identifier, domain) == 1
        assert identifier in casbin.get_user_roles(str(setup_user.id), domain)
    finally:
        casbin.enforcer.remove_grouping_policy(str(setup_user.id), identifier, domain)


def test_role_is_deleted_when_policy_cleanup_fails(
    db, execution_boundary, setup_role, monkeypatch
):
    """Policy cleanup is best effort: its failure is contained in a savepoint
    and the role deletion still commits."""
    command = DeleteRoleCommand(db, nats_publisher=None)
    monkeypatch.setattr(
        get_casbin_repository(),
        "remove_all_policies_for_role",
        Mock(side_effect=RuntimeError("policy cleanup failed")),
    )

    with execution_boundary():
        assert command.execute(setup_role.id) is True

    assert db.query(Role).filter(Role.id == setup_role.id).first() is None


def test_revocation_takes_effect_on_commit(
    db, execution_boundary, setup_role, setup_user, faker
):
    """Routes pass user_id as a UUID; the grant is stored as a string. The
    revocation must still match it (it used to leave the grant in the
    enforcer)."""
    domain = f"tenant-{faker.uuid4()}"
    identifier = str(setup_role.identifier)
    casbin = get_casbin_repository()

    try:
        with execution_boundary():
            CreateMembershipCommand(db, nats_publisher=None).execute(
                role=setup_role, user_id=setup_user.id, domain=domain
            )
        assert identifier in casbin.get_user_roles(str(setup_user.id), domain)

        with execution_boundary():
            DeleteMembershipCommand(db, nats_publisher=None).execute(
                role=setup_role, user_id=setup_user.id, domain=domain
            )
            # Revoked in this transaction, still effective until commit.
            assert identifier in casbin.get_user_roles(str(setup_user.id), domain)

        assert _stored_grants(db, setup_user.id, identifier, domain) == 0
        assert identifier not in casbin.get_user_roles(str(setup_user.id), domain)
    finally:
        casbin.enforcer.remove_grouping_policy(str(setup_user.id), identifier, domain)
