import os
from contextlib import contextmanager
from typing import Optional, List, Tuple
import casbin
from casbin_sqlalchemy_adapter import Adapter
from sqlalchemy import create_engine
from app.config import get_settings
from app.core.logging_config import get_logger
from app.db import current_session, on_commit
from functools import lru_cache

GLOBAL_DOMAIN = "*"


def normalize_domain(domain: Optional[str]) -> str:
    """Map a missing/empty domain to the global wildcard domain.

    The model requires a fixed number of fields on every g/p row
    (g = _, _, _ and p = sub, dom, obj, act), so "no domain" must always be
    written and read as the same value rather than being omitted.
    """
    return domain or GLOBAL_DOMAIN


class ManagedSessionAdapter(Adapter):
    """Casbin adapter that stores rules in the current managed session.

    Inside an execution (request, task) casbin_rule rows are written by the
    execution's session, so they commit or roll back together with the
    memberships, roles and permissions they belong to. Outside one (startup
    policy load, scripts) the adapter uses its own session and commits.
    """

    @contextmanager
    def _session_scope(self):
        session = current_session()
        if session is None:
            with super()._session_scope() as own_session:
                yield own_session
        else:
            yield session


@lru_cache()
def get_casbin_repository():
    return CasbinRepository()


class CasbinRepository:
    """Repository for handling authorization using Casbin.

    Rules live in two places: the casbin_rule table and the enforcer's
    in-memory model, which answers every authorization check. Writes go to
    the table through the adapter, in the current transaction, and are
    applied to the in-memory model only after that transaction commits
    (auto-save is off, so enforcer mutations are memory-only). A rolled-back
    grant therefore never becomes effective, and a failed write raises in the
    request that made it.
    """

    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger()
        self.enforcer = None
        self._initialize_enforcer()

    def _initialize_enforcer(self) -> None:
        """Initialize the Casbin enforcer with PostgreSQL adapter."""
        try:
            # Create database engine for Casbin adapter
            engine = create_engine(self.settings.database_url)

            # Create Casbin adapter
            self.adapter = ManagedSessionAdapter(engine)

            # Get the path to the Casbin model configuration
            model_path = os.path.join(
                os.path.dirname(__file__), "..", "config", "casbin_model.conf"
            )

            # Create enforcer
            self.enforcer = casbin.Enforcer(model_path, self.adapter)
            # Storage writes go through _store_rule/_delete_rules, so enforcer
            # mutations only update the in-memory model.
            self.enforcer.enable_auto_save(False)

            # Load policies
            self.enforcer.load_policy()

            self.logger.debug("Casbin enforcer initialized successfully")

        except Exception:
            raise

    def _rule_stored(self, ptype: str, rule: List[str]) -> bool:
        with self.adapter._session_scope() as session:
            query = session.query(self.adapter._db_class).filter_by(ptype=ptype)
            for index, value in enumerate(rule):
                query = query.filter_by(**{f"v{index}": value})
            return session.query(query.exists()).scalar()

    def _store_rule(self, ptype: str, rule: List[str]) -> None:
        """Insert ``rule`` into casbin_rule unless this transaction already
        has it (the in-memory model only reflects committed rules)."""
        if not self._rule_stored(ptype, rule):
            self.adapter.add_policy(ptype[0], ptype, rule)

    def _delete_rules(self, ptype: str, field_index: int, *values: str) -> bool:
        """Delete the matching casbin_rule rows; True if any existed."""
        return self.adapter.remove_filtered_policy(
            ptype[0], ptype, field_index, *values
        )

    def authorize(
        self,
        user_id: str,
        action: str,
        resource: str,
        domain: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> bool:
        """
        Check if a user is authorized to perform an action on a resource.

        Args:
            user_id: The ID of the user
            action: The action to perform (e.g., 'read', 'write', 'delete')
            resource: The resource type (e.g., 'users', 'documents')
            domain: The domain/tenant for multi-tenancy
            resource_id: Specific resource ID if applicable

        Returns:
            bool: True if authorized, False otherwise
        """
        try:
            # Build the subject (user)
            subject = user_id

            # Build the object (resource)
            if resource_id:
                obj = f"{resource}:{resource_id}"
            else:
                obj = resource

            # Build the action
            act = action

            domain = normalize_domain(domain)
            result = self.enforcer.enforce(subject, domain, obj, act)

            self.logger.info(
                "Authorization check",
                extra={
                    "user_id": user_id,
                    "action": action,
                    "resource": resource,
                    "domain": domain,
                    "allowed": result,
                },
            )

            return result

        except Exception as e:
            self.logger.error(f"Authorization check failed: {e}")
            return False

    def assign_role(
        self,
        user_id: str,
        role: str,
        domain: Optional[str] = None,
        resource: Optional[str] = None,
    ) -> bool:
        """
        Assign a role to a user.

        Args:
            user_id: The ID of the user
            role: The role to assign
            domain: The domain/tenant for the role
            resource: The resource the role applies to

        Returns:
            bool: True if successful, False otherwise
        """
        domain = normalize_domain(domain)

        # Check if role is already assigned
        user_roles = self.enforcer.get_roles_for_user_in_domain(user_id, domain)
        if role in user_roles:
            self.logger.debug(
                f"Role {role} already assigned to user {user_id} in domain {domain}"
            )
            return True

        rule = [str(user_id), role, domain]
        self._store_rule("g", rule)
        on_commit(lambda: self.enforcer.add_grouping_policy(*rule))

        return True

    def remove_role(
        self, user_id: str, role: str, domain: Optional[str] = None
    ) -> bool:
        """
        Remove a role from a user.

        Args:
            user_id: The ID of the user
            role: The role to remove
            domain: The domain/tenant for the role

        Returns:
            bool: True if successful, False otherwise
        """
        domain = normalize_domain(domain)
        rule = [str(user_id), role, domain]
        assigned = self.enforcer.has_grouping_policy(*rule)
        stored = self._delete_rules("g", 0, *rule)
        on_commit(lambda: self.enforcer.remove_grouping_policy(*rule))

        return assigned or stored

    def get_user_roles(self, user_id: str, domain: Optional[str] = None) -> List[str]:
        """
        Get all roles assigned to a user.

        Args:
            user_id: The ID of the user
            domain: The domain/tenant to check roles for

        Returns:
            List[str]: List of role names
        """
        domain = normalize_domain(domain)
        roles = self.enforcer.get_roles_for_user_in_domain(user_id, domain)

        return roles

    def get_user_permissions(
        self, user_id: str, domain: Optional[str] = None, resource: Optional[str] = None
    ) -> List[Tuple[str, ...]]:
        """
        Get all permissions for a user, including those inherited via roles.

        Args:
            user_id: The ID of the user
            domain: The domain/tenant to check permissions for
            resource: The resource to filter permissions by

        Returns:
            List[Tuple[str, ...]]: List of permission tuples
        """
        domain = normalize_domain(domain)
        # Use implicit permissions to include those inherited via roles
        permissions = self.enforcer.get_implicit_permissions_for_user(user_id, domain)

        # Filter by resource if specified
        if resource:
            # For domain-based model, resource is at index 2
            permissions = [p for p in permissions if len(p) > 2 and p[2] == resource]

        return permissions

    def add_policy(
        self, subject: str, obj: str, action: str, domain: Optional[str] = None
    ) -> bool:
        """
        Add a policy rule.

        Args:
            subject: The subject (user or role)
            obj: The object (resource)
            action: The action
            domain: The domain/tenant

        Returns:
            bool: True if successful, False otherwise
        """
        domain = normalize_domain(domain)

        # Check if policy already exists
        policy_exists = self.enforcer.has_policy(subject, domain, obj, action)
        if policy_exists:
            self.logger.debug(
                f"Policy already exists: {subject} -> {obj} -> {action} in domain {domain}"
            )
            return True

        rule = [subject, domain, obj, action]
        self._store_rule("p", rule)
        on_commit(lambda: self.enforcer.add_named_policy("p", rule))

        return True

    def remove_policy(
        self, subject: str, obj: str, action: str, domain: Optional[str] = None
    ) -> bool:
        """
        Remove a policy rule.

        Args:
            subject: The subject (user or role)
            obj: The object (resource)
            action: The action
            domain: The domain/tenant

        Returns:
            bool: True if successful, False otherwise
        """
        domain = normalize_domain(domain)
        rule = [subject, domain, obj, action]
        existed = self.enforcer.has_policy(*rule)
        stored = self._delete_rules("p", 0, *rule)
        on_commit(lambda: self.enforcer.remove_policy(*rule))

        return existed or stored

    def remove_all_policies_for_role(self, role_identifier: str) -> int:
        """
        Remove all policies for a role across all domains.

        Args:
            role_identifier: The role identifier (subject in policies)

        Returns:
            int: Number of policies removed
        """
        # Get all policies for this role before removing them (for counting)
        # Policies are stored as [subject, domain, obj, action] where subject is role_identifier
        all_policies = self.enforcer.get_filtered_policy(0, role_identifier)

        # Remove all policies where subject (index 0) matches role_identifier
        self._delete_rules("p", 0, role_identifier)
        on_commit(lambda: self.enforcer.remove_filtered_policy(0, role_identifier))

        return len(all_policies)

    def get_users_for_role(self, role: str, domain: Optional[str] = None) -> List[str]:
        """
        Get all users that have a specific role.

        Args:
            role: The role to search for
            domain: The domain/tenant to check roles for

        Returns:
            List[str]: List of user IDs that have the specified role
        """
        domain = normalize_domain(domain)
        users = self.enforcer.get_users_for_role_in_domain(role, domain)

        return users

    def clear_all_policies(self) -> bool:
        """
        Clear all policies and role assignments from the Casbin enforcer.
        This is primarily used for testing purposes.

        Returns:
            bool: True if successful, False otherwise
        """
        # Get all users and their roles BEFORE clearing policies
        all_users = self.enforcer.get_all_subjects()
        users_to_clear = []

        for user in all_users:
            # Get all roles for this user (both domain-specific and global)
            user_roles = self.enforcer.get_roles_for_user(user)
            domain_roles = []

            # Also check domain-specific roles
            for domain in ["*", "global", "admin"]:
                try:
                    domain_user_roles = self.enforcer.get_roles_for_user_in_domain(
                        user, domain
                    )
                    domain_roles.extend([(role, domain) for role in domain_user_roles])
                except Exception:
                    # Domain might not exist, continue
                    pass

            users_to_clear.append((user, user_roles, domain_roles))

        # Clear all policies first
        self.enforcer.clear_policy()

        # Now remove all role assignments
        for user, user_roles, domain_roles in users_to_clear:
            # Remove global roles
            for role in user_roles:
                try:
                    self.enforcer.delete_role_for_user(user, role)
                except Exception:
                    # Role might already be removed, continue
                    pass

            # Remove domain-specific roles
            for role, domain in domain_roles:
                try:
                    self.enforcer.delete_role_for_user_in_domain(user, role, domain)
                except Exception:
                    # Role might already be removed, continue
                    pass

        # Save the empty policy
        self.enforcer.save_policy()

        return True
