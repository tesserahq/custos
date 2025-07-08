"""
Role Template Service for managing role definitions across multiple domains
"""

import logging
from typing import Dict, List, Any, Optional
from .casbin_service import casbin_service
from .role_definition_service import role_definition_service


class RoleTemplateService:
    """Service for managing role templates and applying them across domains"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.templates_dir = "config/templates"

    def create_role_template(
        self, template_name: str, role_config: Dict[str, Any]
    ) -> bool:
        """
        Create a role template that can be applied to multiple domains.

        Args:
            template_name: Name of the template
            role_config: Role configuration (same format as role config files)

        Returns:
            bool: True if successful
        """
        try:
            import yaml
            import os

            # Ensure templates directory exists
            os.makedirs(self.templates_dir, exist_ok=True)

            template_file = f"{self.templates_dir}/{template_name}.yaml"

            with open(template_file, "w") as f:
                yaml.dump(role_config, f, default_flow_style=False)

            self.logger.info(f"Created role template: {template_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create role template {template_name}: {e}")
            return False

    def get_role_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a role template by name.

        Args:
            template_name: Name of the template

        Returns:
            Dict containing role configuration or None if not found
        """
        try:
            import yaml
            import os

            template_file = f"{self.templates_dir}/{template_name}.yaml"

            if not os.path.exists(template_file):
                return None

            with open(template_file, "r") as f:
                config = yaml.safe_load(f)

            return config

        except Exception as e:
            self.logger.error(f"Failed to load role template {template_name}: {e}")
            return None

    def list_role_templates(self) -> List[str]:
        """
        List all available role templates.

        Returns:
            List of template names
        """
        try:
            import os

            if not os.path.exists(self.templates_dir):
                return []

            templates = []
            for file in os.listdir(self.templates_dir):
                if file.endswith(".yaml") or file.endswith(".yml"):
                    templates.append(file[:-5] if file.endswith(".yaml") else file[:-4])

            return templates

        except Exception as e:
            self.logger.error(f"Failed to list role templates: {e}")
            return []

    def apply_template_to_domain(
        self, template_name: str, domain: str, overwrite_existing: bool = False
    ) -> Dict[str, bool]:
        """
        Apply a role template to a specific domain.

        Args:
            template_name: Name of the template to apply
            domain: Target domain
            overwrite_existing: Whether to overwrite existing roles

        Returns:
            Dict[str, bool]: Results for each role
        """
        try:
            config = self.get_role_template(template_name)
            if not config:
                return {"error": f"Template {template_name} not found"}

            results = {}

            for role_name, role_config in config.get("roles", {}).items():
                # Check if role already exists
                existing_permissions = role_definition_service.get_role_permissions(
                    role_name, domain
                )

                if existing_permissions and not overwrite_existing:
                    self.logger.warning(
                        f"Role {role_name} already exists in domain {domain}, skipping"
                    )
                    results[role_name] = False
                    continue

                # Define the role
                success = self._define_role_from_config(role_name, domain, role_config)
                results[role_name] = success

            self.logger.info(
                f"Applied template {template_name} to domain {domain}: {results}"
            )
            return results

        except Exception as e:
            self.logger.error(
                f"Failed to apply template {template_name} to domain {domain}: {e}"
            )
            return {"error": str(e)}

    def apply_template_to_multiple_domains(
        self, template_name: str, domains: List[str], overwrite_existing: bool = False
    ) -> Dict[str, Dict[str, bool]]:
        """
        Apply a role template to multiple domains.

        Args:
            template_name: Name of the template to apply
            domains: List of target domains
            overwrite_existing: Whether to overwrite existing roles

        Returns:
            Dict[domain, Dict[str, bool]]: Results for each domain
        """
        results = {}

        for domain in domains:
            domain_results = self.apply_template_to_domain(
                template_name, domain, overwrite_existing
            )
            results[domain] = domain_results

        self.logger.info(f"Applied template {template_name} to {len(domains)} domains")
        return results

    def update_template_and_apply(
        self,
        template_name: str,
        updated_config: Dict[str, Any],
        domains: List[str],
        overwrite_existing: bool = True,
    ) -> Dict[str, Dict[str, bool]]:
        """
        Update a template and apply it to multiple domains.

        Args:
            template_name: Name of the template to update
            updated_config: Updated role configuration
            domains: List of domains to apply to
            overwrite_existing: Whether to overwrite existing roles

        Returns:
            Dict[domain, Dict[str, bool]]: Results for each domain
        """
        # Update the template
        success = self.create_role_template(template_name, updated_config)
        if not success:
            return {"error": f"Failed to update template {template_name}"}

        # Apply to all domains
        return self.apply_template_to_multiple_domains(
            template_name, domains, overwrite_existing
        )

    def add_permission_to_template(
        self, template_name: str, role_name: str, resource: str, action: str
    ) -> bool:
        """
        Add a permission to a specific role in a template.

        Args:
            template_name: Name of the template
            role_name: Name of the role to update
            resource: Resource to add permission for
            action: Action to add permission for

        Returns:
            bool: True if successful
        """
        try:
            config = self.get_role_template(template_name)
            if not config:
                return False

            # Add permission to the role
            if "roles" not in config:
                config["roles"] = {}

            if role_name not in config["roles"]:
                config["roles"][role_name] = {"permissions": {}}

            if "permissions" not in config["roles"][role_name]:
                config["roles"][role_name]["permissions"] = {}

            if resource not in config["roles"][role_name]["permissions"]:
                config["roles"][role_name]["permissions"][resource] = []

            if action not in config["roles"][role_name]["permissions"][resource]:
                config["roles"][role_name]["permissions"][resource].append(action)

            # Save updated template
            return self.create_role_template(template_name, config)

        except Exception as e:
            self.logger.error(
                f"Failed to add permission to template {template_name}: {e}"
            )
            return False

    def remove_permission_from_template(
        self, template_name: str, role_name: str, resource: str, action: str
    ) -> bool:
        """
        Remove a permission from a specific role in a template.

        Args:
            template_name: Name of the template
            role_name: Name of the role to update
            resource: Resource to remove permission for
            action: Action to remove permission for

        Returns:
            bool: True if successful
        """
        try:
            config = self.get_role_template(template_name)
            if not config:
                return False

            # Remove permission from the role
            if (
                "roles" in config
                and role_name in config["roles"]
                and "permissions" in config["roles"][role_name]
                and resource in config["roles"][role_name]["permissions"]
            ):

                permissions = config["roles"][role_name]["permissions"][resource]
                if action in permissions:
                    permissions.remove(action)

                # Remove empty resource entries
                if not permissions:
                    del config["roles"][role_name]["permissions"][resource]

            # Save updated template
            return self.create_role_template(template_name, config)

        except Exception as e:
            self.logger.error(
                f"Failed to remove permission from template {template_name}: {e}"
            )
            return False

    def _define_role_from_config(
        self, role_name: str, domain: str, role_config: Dict[str, Any]
    ) -> bool:
        """
        Define a role from configuration.

        Args:
            role_name: Name of the role
            domain: Domain for the role
            role_config: Role configuration

        Returns:
            bool: True if successful
        """
        try:
            permissions = []

            # Extract permissions from role config
            if "permissions" in role_config:
                for resource, actions in role_config["permissions"].items():
                    if isinstance(actions, list):
                        for action in actions:
                            permissions.append((resource, action))
                    else:
                        permissions.append((resource, actions))

            # Define the role using role definition service
            return role_definition_service.define_custom_role(
                role_name, domain, permissions
            )

        except Exception as e:
            self.logger.error(f"Failed to define role {role_name} from config: {e}")
            return False


# Global instance
role_template_service = RoleTemplateService()
