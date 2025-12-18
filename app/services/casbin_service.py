import os
from typing import Optional, List, Tuple
import casbin
from casbin_sqlalchemy_adapter import Adapter
from sqlalchemy import create_engine, text
from app.config import get_settings
from app.core.logging_config import get_logger


class CasbinService:
    """Service for handling authorization using Casbin."""

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

            # Load policies
            self.enforcer.load_policy()

            self.logger.info("Casbin enforcer initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize Casbin enforcer: {e}")
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

            # For multi-tenancy, use domain as the fourth parameter
            if domain:
                result = self.enforcer.enforce(subject, domain, obj, act)
            else:
                result = self.enforcer.enforce(subject, obj, act)

            self.logger.info(
                f"Authorization check: user={user_id}, action={action}, "
                f"resource={resource}, domain={domain}, allowed={result}"
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
        try:
            if domain:
                # Check if role is already assigned
                user_roles = self.enforcer.get_roles_for_user_in_domain(user_id, domain)
                if role in user_roles:
                    self.logger.debug(
                        f"Role {role} already assigned to user {user_id} in domain {domain}"
                    )
                    return True

                # For multi-tenancy, use domain-based role assignment
                success = self.enforcer.add_role_for_user_in_domain(
                    user_id, role, domain
                )
            else:
                # Check if role is already assigned
                user_roles = self.enforcer.get_roles_for_user(user_id)
                if role in user_roles:
                    self.logger.debug(f"Role {role} already assigned to user {user_id}")
                    return True

                # For global roles
                success = self.enforcer.add_role_for_user(user_id, role)

            return success

        except Exception as e:
            self.logger.error(f"Role assignment failed: {e}")
            return False

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
        try:
            if domain:
                success = self.enforcer.delete_roles_for_user_in_domain(
                    user_id, role, domain
                )
            else:
                success = self.enforcer.delete_role_for_user(user_id, role)

            return success

        except Exception as e:
            self.logger.error(f"Role removal failed: {e}")
            return False

    def get_user_roles(self, user_id: str, domain: Optional[str] = None) -> List[str]:
        """
        Get all roles assigned to a user.

        Args:
            user_id: The ID of the user
            domain: The domain/tenant to check roles for

        Returns:
            List[str]: List of role names
        """
        try:
            if domain:
                roles = self.enforcer.get_roles_for_user_in_domain(user_id, domain)
            else:
                roles = self.enforcer.get_roles_for_user(user_id)

            return roles

        except Exception as e:
            self.logger.error(f"Failed to get roles for user {user_id}: {e}")
            return []

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
        try:
            if domain:
                # Use implicit permissions to include those inherited via roles
                permissions = self.enforcer.get_implicit_permissions_for_user(
                    user_id, domain
                )
            else:
                permissions = self.enforcer.get_implicit_permissions_for_user(user_id)

            # Filter by resource if specified
            if resource:
                # For domain-based model, resource is at index 2
                permissions = [
                    p for p in permissions if len(p) > 2 and p[2] == resource
                ]

            return permissions

        except Exception as e:
            self.logger.error(f"Failed to get permissions for user {user_id}: {e}")
            return []

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
        try:
            if domain:
                # Check if policy already exists
                policy_exists = self.enforcer.has_policy(subject, domain, obj, action)
                if policy_exists:
                    self.logger.debug(
                        f"Policy already exists: {subject} -> {obj} -> {action} in domain {domain}"
                    )
                    return True

                # For domain-based model, use add_named_policy to specify the policy type
                success = self.enforcer.add_named_policy(
                    "p", [subject, domain, obj, action]
                )
            else:
                # Check if policy already exists
                policy_exists = self.enforcer.has_policy(subject, obj, action)
                if policy_exists:
                    self.logger.debug(
                        f"Policy already exists: {subject} -> {obj} -> {action}"
                    )
                    return True

                success = self.enforcer.add_policy(subject, obj, action)

            return success

        except Exception as e:
            self.logger.error(f"Failed to add policy: {e}")
            return False

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
        try:
            if domain:
                success = self.enforcer.remove_policy(subject, domain, obj, action)
            else:
                success = self.enforcer.remove_policy(subject, obj, action)

            return success

        except Exception as e:
            self.logger.error(f"Failed to remove policy: {e}")
            return False

    def get_users_for_role(self, role: str, domain: Optional[str] = None) -> List[str]:
        """
        Get all users that have a specific role.

        Args:
            role: The role to search for
            domain: The domain/tenant to check roles for

        Returns:
            List[str]: List of user IDs that have the specified role
        """
        try:
            if domain:
                users = self.enforcer.get_users_for_role_in_domain(role, domain)
            else:
                users = self.enforcer.get_users_for_role(role)

            return users

        except Exception as e:
            self.logger.error(f"Failed to get users for role {role}: {e}")
            return []

    def clear_all_policies(self) -> bool:
        """
        Clear all policies and role assignments from the Casbin enforcer.
        This is primarily used for testing purposes.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
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
                        domain_roles.extend(
                            [(role, domain) for role in domain_user_roles]
                        )
                    except:
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
                    except:
                        # Role might already be removed, continue
                        pass

                # Remove domain-specific roles
                for role, domain in domain_roles:
                    try:
                        self.enforcer.delete_role_for_user_in_domain(user, role, domain)
                    except:
                        # Role might already be removed, continue
                        pass

            # Save the empty policy
            self.enforcer.save_policy()

            self.logger.info(
                "All Casbin policies and role assignments cleared successfully"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to clear Casbin policies: {e}")
            return False
