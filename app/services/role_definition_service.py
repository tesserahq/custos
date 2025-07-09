from typing import Dict, List, Optional
from app.services.casbin_service import casbin_service
from app.core.logging_config import get_logger


class RoleDefinitionService:
    """Service for defining and managing common roles in the authorization system."""

    def __init__(self):
        self.logger = get_logger()

    def define_admin_role(self, domain: str) -> bool:
        """
        Define admin role with full permissions for a domain.

        Args:
            domain: The domain/tenant for the role

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Define admin permissions
            admin_permissions = [
                # User management
                ("admin", domain, "users", "read"),
                ("admin", domain, "users", "write"),
                ("admin", domain, "users", "delete"),
                ("admin", domain, "users", "create"),
                # Project management
                ("admin", domain, "projects", "read"),
                ("admin", domain, "projects", "write"),
                ("admin", domain, "projects", "delete"),
                ("admin", domain, "projects", "create"),
                # Document management
                ("admin", domain, "documents", "read"),
                ("admin", domain, "documents", "write"),
                ("admin", domain, "documents", "delete"),
                ("admin", domain, "documents", "create"),
                # Role management
                ("admin", domain, "roles", "read"),
                ("admin", domain, "roles", "write"),
                ("admin", domain, "roles", "delete"),
                ("admin", domain, "roles", "create"),
                # Account settings
                ("admin", domain, "settings", "read"),
                ("admin", domain, "settings", "write"),
            ]

            success_count = 0
            for subject, dom, obj, action in admin_permissions:
                if casbin_service.add_policy(subject, obj, action, domain=dom):
                    success_count += 1
                else:
                    self.logger.warning(
                        f"Failed to add policy: {subject} -> {obj} -> {action}"
                    )

            self.logger.info(
                f"Admin role defined for domain {domain}: {success_count}/{len(admin_permissions)} policies added"
            )

            # Consider it successful if at least 80% of policies were added
            # This allows for some duplicates while ensuring the role is properly defined
            return success_count >= len(admin_permissions) * 0.8

        except Exception as e:
            self.logger.error(f"Failed to define admin role for domain {domain}: {e}")
            return False

    def define_editor_role(self, domain: str) -> bool:
        """
        Define editor role with read/write permissions for a domain.

        Args:
            domain: The domain/tenant for the role

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Define editor permissions
            editor_permissions = [
                # User management (read only)
                ("editor", domain, "users", "read"),
                # Project management
                ("editor", domain, "projects", "read"),
                ("editor", domain, "projects", "write"),
                ("editor", domain, "projects", "create"),
                # Document management
                ("editor", domain, "documents", "read"),
                ("editor", domain, "documents", "write"),
                ("editor", domain, "documents", "create"),
                # Settings (read only)
                ("editor", domain, "settings", "read"),
            ]

            success_count = 0
            for subject, dom, obj, action in editor_permissions:
                if casbin_service.add_policy(subject, obj, action, domain=dom):
                    success_count += 1
                else:
                    self.logger.warning(
                        f"Failed to add policy: {subject} -> {obj} -> {action}"
                    )

            self.logger.info(
                f"Editor role defined for domain {domain}: {success_count}/{len(editor_permissions)} policies added"
            )

            # Consider it successful if at least 80% of policies were added
            return success_count >= len(editor_permissions) * 0.8

        except Exception as e:
            self.logger.error(f"Failed to define editor role for domain {domain}: {e}")
            return False

    def define_viewer_role(self, domain: str) -> bool:
        """
        Define viewer role with read-only permissions for a domain.

        Args:
            domain: The domain/tenant for the role

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Define viewer permissions (read-only)
            viewer_permissions = [
                # User management (read only)
                ("viewer", domain, "users", "read"),
                # Project management (read only)
                ("viewer", domain, "projects", "read"),
                # Document management (read only)
                ("viewer", domain, "documents", "read"),
                # Settings (read only)
                ("viewer", domain, "settings", "read"),
            ]

            success_count = 0
            for subject, dom, obj, action in viewer_permissions:
                if casbin_service.add_policy(subject, obj, action, domain=dom):
                    success_count += 1
                else:
                    self.logger.warning(
                        f"Failed to add policy: {subject} -> {obj} -> {action}"
                    )

            self.logger.info(
                f"Viewer role defined for domain {domain}: {success_count}/{len(viewer_permissions)} policies added"
            )

            # Consider it successful if at least 80% of policies were added
            return success_count >= len(viewer_permissions) * 0.8

        except Exception as e:
            self.logger.error(f"Failed to define viewer role for domain {domain}: {e}")
            return False

    def define_system_admin_role(self, domain: str = "*") -> bool:
        """
        Define system admin role with permissions to manage service accounts and roles.
        Args:
            domain: The domain for the role (defaults to "*" for global access)
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Only allow management of service accounts and roles
            permissions = [
                ("system_admin", domain, "service_accounts", "create"),
                ("system_admin", domain, "service_accounts", "read"),
                ("system_admin", domain, "service_accounts", "write"),
                ("system_admin", domain, "service_accounts", "delete"),
                ("system_admin", domain, "roles", "create"),
                ("system_admin", domain, "roles", "read"),
                ("system_admin", domain, "roles", "write"),
                ("system_admin", domain, "roles", "delete"),
                ("system_admin", domain, "roles", "assign"),
            ]
            success_count = 0
            for subject, dom, obj, action in permissions:
                if casbin_service.add_policy(subject, obj, action, domain=dom):
                    success_count += 1
                else:
                    self.logger.warning(
                        f"Failed to add system admin policy: {subject} -> {obj} -> {action}"
                    )
            self.logger.info(
                f"System admin role defined for domain {domain}: {success_count}/{len(permissions)} policies added"
            )
            return success_count >= len(permissions) * 0.8
        except Exception as e:
            self.logger.error(
                f"Failed to define system admin role for domain {domain}: {e}"
            )
            return False

    def define_custom_role(
        self, role_name: str, domain: str, permissions: List[tuple]
    ) -> bool:
        """
        Define a custom role with specific permissions.

        Args:
            role_name: Name of the custom role
            domain: The domain/tenant for the role
            permissions: List of (resource, action) tuples

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            success_count = 0
            for resource, action in permissions:
                if casbin_service.add_policy(
                    role_name, resource, action, domain=domain
                ):
                    success_count += 1
                else:
                    self.logger.warning(
                        f"Failed to add policy: {role_name} -> {resource} -> {action}"
                    )

            self.logger.info(
                f"Custom role '{role_name}' defined for domain {domain}: {success_count}/{len(permissions)} policies added"
            )

            # Consider it successful if at least 80% of policies were added
            return success_count >= len(permissions) * 0.8

        except Exception as e:
            self.logger.error(
                f"Failed to define custom role '{role_name}' for domain {domain}: {e}"
            )
            return False

    def setup_default_roles(self, domain: str) -> Dict[str, bool]:
        """
        Set up all default roles for a domain.

        Args:
            domain: The domain/tenant

        Returns:
            Dict[str, bool]: Results for each role setup
        """
        results = {}

        # Define all default roles
        results["admin"] = self.define_admin_role(domain)
        results["editor"] = self.define_editor_role(domain)
        results["viewer"] = self.define_viewer_role(domain)

        self.logger.info(
            f"Default roles setup completed for domain {domain}: {results}"
        )
        return results

    def get_role_permissions(self, role_name: str, domain: str) -> List[tuple]:
        """
        Get all permissions for a specific role.

        Args:
            role_name: Name of the role
            domain: The domain/tenant

        Returns:
            List[tuple]: List of (resource, action) tuples
        """
        try:
            # Get all policies for the role in the domain
            policies = casbin_service.enforcer.get_filtered_policy(0, role_name)

            # Filter by domain and extract resource/action pairs
            permissions = []
            for policy in policies:
                if len(policy) >= 4 and policy[1] == domain:  # Check domain matches
                    permissions.append((policy[2], policy[3]))  # (resource, action)

            return permissions

        except Exception as e:
            self.logger.error(
                f"Failed to get permissions for role '{role_name}' in domain {domain}: {e}"
            )
            return []

    def list_defined_roles(self, domain: str) -> List[str]:
        """
        List all roles that have been defined for a domain.

        Args:
            domain: The domain/tenant

        Returns:
            List[str]: List of role names
        """
        try:
            # Get all policies and extract unique role names for the domain
            policies = casbin_service.enforcer.get_policy()
            roles = set()

            for policy in policies:
                if len(policy) >= 4 and policy[1] == domain:  # Check domain matches
                    roles.add(policy[0])  # Add role name

            return list(roles)

        except Exception as e:
            self.logger.error(f"Failed to list roles for domain {domain}: {e}")
            return []


# Global instance
role_definition_service = RoleDefinitionService()
