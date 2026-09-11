"""Regression tests for CasbinRepository domain normalization.

These use a real (test-database-backed) Casbin enforcer rather than a mock,
because the bug this guards against only manifests when the enforcer reloads
its policy from storage: writing a grouping-policy ("g") row without a domain
alongside rows that do have a domain leaves mixed field widths in the
casbin_rule table, which crashes `Enforcer.load_policy()` on the *next*
process start with `RuntimeError: grouping policy elements do not meet role
definition`. A mocked casbin_repository would never catch this.
"""

from app.repositories.casbin_repository import CasbinRepository


class TestCasbinRepositoryDomainNormalization:
    def test_assign_role_without_domain_survives_reload(self, engine, faker):
        """A role assigned with no domain must reload without error."""
        repo = CasbinRepository()
        user_id = str(faker.uuid4())
        role = f"test-role-{faker.uuid4()}"

        try:
            assert repo.assign_role(user_id, role) is True

            # This is the exact operation that crashed in production: a
            # fresh enforcer re-reading the persisted grouping policy.
            reloaded = CasbinRepository()
            assert role in reloaded.get_user_roles(user_id)
        finally:
            repo.remove_role(user_id, role)

    def test_mixed_domain_and_no_domain_assignments_survive_reload(self, engine, faker):
        """Assigning roles with and without an explicit domain must produce
        grouping-policy rows of a consistent shape, so reloading the
        enforcer from storage never raises."""
        repo = CasbinRepository()
        user_id = str(faker.uuid4())
        role_no_domain = f"role-no-domain-{faker.uuid4()}"
        role_with_domain = f"role-with-domain-{faker.uuid4()}"
        domain = f"tenant-{faker.uuid4()}"

        try:
            assert repo.assign_role(user_id, role_no_domain) is True
            assert repo.assign_role(user_id, role_with_domain, domain=domain) is True

            # Previously: reloading here raised RuntimeError because the
            # two roles above were written as g rows of different widths.
            reloaded = CasbinRepository()
            assert role_no_domain in reloaded.get_user_roles(user_id)
            assert role_with_domain in reloaded.get_user_roles(user_id, domain=domain)
        finally:
            repo.remove_role(user_id, role_no_domain)
            repo.remove_role(user_id, role_with_domain, domain=domain)

    def test_assign_role_without_domain_writes_wildcard_domain_row(self, engine, faker):
        """A missing domain must be stored as the global wildcard domain,
        not omitted, so every g row has the same number of fields."""
        repo = CasbinRepository()
        user_id = str(faker.uuid4())
        role = f"test-role-{faker.uuid4()}"

        try:
            repo.assign_role(user_id, role)

            rows = repo.enforcer.get_filtered_grouping_policy(0, user_id)
            matching = [r for r in rows if r[1] == role]
            assert len(matching) == 1
            assert len(matching[0]) == 3
            assert matching[0][2] == "*"
        finally:
            repo.remove_role(user_id, role)
