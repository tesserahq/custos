import os
from typing import Optional, List, Tuple
import casbin
from casbin_sqlalchemy_adapter import Adapter
from sqlalchemy import create_engine
from app.config import get_settings
from app.core.logging_config import get_logger
from functools import lru_cache

GLOBAL_DOMAIN = "*"


@lru_cache()
def get_casbin_repository():
    return CasbinRepository()


class CasbinRepository:
    """Repository for handling authorization using Casbin."""

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
            adapter = Adapter(engine)

            # Get the path to the Casbin model configuration
            model_path = os.path.join(
                os.path.dirname(__file__), "..", "config", "casbin_model.conf"
            )

            # Create enforcer
            self.enforcer = casbin.Enforcer(model_path, adapter)
            self.enforcer.enable_auto_save(True)

            # Load policies
            self.enforcer.load_policy()

            self.logger.debug("Casbin enforcer initialized successfully")

        except Exception:
            raise

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

            # The model always expects a domain (r = sub, dom, obj, act);
            # missing domain means "global" scope.
            domain = domain or GLOBAL_DOMAIN
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
        # The model always expects a domain (g = _, _, _); missing domain
        # means "global" scope. Always writing through the domain-scoped API
        # keeps every grouping-policy row the same width.
        domain = domain or GLOBAL_DOMAIN

        # Check if role is already assigned
        user_roles = self.enforcer.get_roles_for_user_in_domain(user_id, domain)
        if role in user_roles:
            self.logger.debug(
                f"Role {role} already assigned to user {user_id} in domain {domain}"
            )
            return True

        success = self.enforcer.add_role_for_user_in_domain(user_id, role, domain)

        return success

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
        domain = domain or GLOBAL_DOMAIN
        success = self.enforcer.delete_roles_for_user_in_domain(user_id, role, domain)

        return success

    def get_user_roles(self, user_id: str, domain: Optional[str] = None) -> List[str]:
        """
        Get all roles assigned to a user.

        Args:
            user_id: The ID of the user
            domain: The domain/tenant to check roles for

        Returns:
            List[str]: List of role names
        """
        domain = domain or GLOBAL_DOMAIN
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
        domain = domain or GLOBAL_DOMAIN
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
        domain = domain or GLOBAL_DOMAIN

        # Check if policy already exists
        policy_exists = self.enforcer.has_policy(subject, domain, obj, action)
        if policy_exists:
            self.logger.debug(
                f"Policy already exists: {subject} -> {obj} -> {action} in domain {domain}"
            )
            return True

        # For domain-based model, use add_named_policy to specify the policy type
        success = self.enforcer.add_named_policy("p", [subject, domain, obj, action])

        return success

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
        domain = domain or GLOBAL_DOMAIN
        success = self.enforcer.remove_policy(subject, domain, obj, action)

        return success

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

        if not all_policies:
            return 0

        # Remove all policies for this role using remove_filtered_policy
        # This removes all policies where subject (index 0) matches role_identifier
        removed = self.enforcer.remove_filtered_policy(0, role_identifier)

        if removed:
            return len(all_policies)
        else:
            self.logger.warning(
                f"Failed to remove policies for role '{role_identifier}'"
            )
            return 0

    def get_users_for_role(self, role: str, domain: Optional[str] = None) -> List[str]:
        """
        Get all users that have a specific role.

        Args:
            role: The role to search for
            domain: The domain/tenant to check roles for

        Returns:
            List[str]: List of user IDs that have the specified role
        """
        domain = domain or GLOBAL_DOMAIN
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
