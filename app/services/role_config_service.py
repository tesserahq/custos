import os
import yaml
import csv
from typing import Dict, List, Optional, Any
from pathlib import Path
from app.services.casbin_service import casbin_service
from app.core.logging_config import get_logger


class RoleConfigService:
    """Service for loading role definitions from configuration files."""

    def __init__(self):
        self.logger = get_logger()
        self.config_dir = Path(__file__).parent.parent / "config"

    def load_roles_from_yaml(self, config_file: str = "roles.yaml") -> Dict[str, Any]:
        """
        Load role definitions from a YAML configuration file.

        Args:
            config_file: Name of the YAML configuration file

        Returns:
            Dict containing role definitions
        """
        try:
            config_path = self.config_dir / config_file
            if not config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")

            with open(config_path, "r") as file:
                config = yaml.safe_load(file)

            self.logger.info(f"Loaded role configuration from {config_file}")
            return config

        except Exception as e:
            self.logger.error(
                f"Failed to load YAML configuration from {config_file}: {e}"
            )
            raise

    def load_roles_from_yaml_content(self, yaml_content: str) -> Dict[str, Any]:
        """
        Load role definitions from YAML content string.

        Args:
            yaml_content: YAML content as a string

        Returns:
            Dict containing role definitions
        """
        try:
            config = yaml.safe_load(yaml_content)
            self.logger.info("Loaded role configuration from YAML content")
            return config

        except yaml.YAMLError as e:
            self.logger.error(f"Failed to parse YAML content: {e}")
            raise ValueError(f"Invalid YAML content: {e}")
        except Exception as e:
            self.logger.error(f"Failed to load YAML configuration from content: {e}")
            raise

    def load_roles_from_csv(self, config_file: str = "roles.csv") -> List[List[str]]:
        """
        Load role definitions from a CSV configuration file.

        Args:
            config_file: Name of the CSV configuration file

        Returns:
            List of policy rules as lists
        """
        try:
            config_path = self.config_dir / config_file
            if not config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")

            policies = []
            with open(config_path, "r") as file:
                csv_reader = csv.reader(file)
                for row in csv_reader:
                    # Skip comments and empty lines
                    if row and not row[0].startswith("#"):
                        # Strip whitespace from each field
                        cleaned_row = [field.strip() for field in row]
                        policies.append(cleaned_row)

            self.logger.info(f"Loaded {len(policies)} policies from {config_file}")
            return policies

        except Exception as e:
            self.logger.error(
                f"Failed to load CSV configuration from {config_file}: {e}"
            )
            raise

    def define_roles_from_yaml(
        self, domain: str, config_file: str = "roles.yaml"
    ) -> Dict[str, bool]:
        """
        Define roles for a domain using YAML configuration.

        Args:
            domain: The domain/tenant for the roles
            config_file: Name of the YAML configuration file

        Returns:
            Dict[str, bool]: Results for each role setup
        """
        try:
            config = self.load_roles_from_yaml(config_file)
            results = {}

            for role_name, role_config in config.get("roles", {}).items():
                success = self._define_role_from_config(role_name, domain, role_config)
                results[role_name] = success

            self.logger.info(f"Defined roles from YAML for domain {domain}: {results}")
            return results

        except Exception as e:
            self.logger.error(
                f"Failed to define roles from YAML for domain {domain}: {e}"
            )
            return {}

    def define_roles_from_yaml_content(
        self, domain: str, yaml_content: str
    ) -> Dict[str, bool]:
        """
        Define roles for a domain using YAML content.

        Args:
            domain: The domain/tenant for the roles
            yaml_content: YAML content as a string

        Returns:
            Dict[str, bool]: Results for each role setup
        """
        try:
            config = self.load_roles_from_yaml_content(yaml_content)
            results = {}

            for role_name, role_config in config.get("roles", {}).items():
                success = self._define_role_from_config(role_name, domain, role_config)
                results[role_name] = success

            self.logger.info(
                f"Defined roles from YAML content for domain {domain}: {results}"
            )
            return results

        except Exception as e:
            self.logger.error(
                f"Failed to define roles from YAML content for domain {domain}: {e}"
            )
            return {}

    def define_roles_from_csv(
        self, domain: str, config_file: str = "roles.csv"
    ) -> Dict[str, bool]:
        """
        Define roles for a domain using CSV configuration.

        Args:
            domain: The domain/tenant for the roles
            config_file: Name of the CSV configuration file

        Returns:
            Dict[str, bool]: Results for each role setup
        """
        try:
            policies = self.load_roles_from_csv(config_file)
            results = {}
            role_policies = {}

            # Group policies by role
            for policy in policies:
                if len(policy) >= 4:
                    role = policy[1]
                    resource = policy[3]
                    action = policy[4]

                    if role not in role_policies:
                        role_policies[role] = []
                    role_policies[role].append((resource, action))

            # Define each role
            for role_name, permissions in role_policies.items():
                success = self._define_role_permissions(role_name, domain, permissions)
                results[role_name] = success

            self.logger.info(f"Defined roles from CSV for domain {domain}: {results}")
            return results

        except Exception as e:
            self.logger.error(
                f"Failed to define roles from CSV for domain {domain}: {e}"
            )
            return {}

    def _define_role_from_config(
        self, role_name: str, domain: str, role_config: Dict[str, Any]
    ) -> bool:
        """
        Define a role from YAML configuration.

        Args:
            role_name: Name of the role
            domain: The domain/tenant for the role
            role_config: Role configuration dictionary

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            permissions = []
            role_permissions = role_config.get("permissions", {})

            for resource, actions in role_permissions.items():
                for action in actions:
                    permissions.append((resource, action))

            return self._define_role_permissions(role_name, domain, permissions)

        except Exception as e:
            self.logger.error(f"Failed to define role {role_name} from config: {e}")
            return False

    def _define_role_permissions(
        self, role_name: str, domain: str, permissions: List[tuple]
    ) -> bool:
        """
        Define permissions for a role.

        Args:
            role_name: Name of the role
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
                f"Role '{role_name}' defined for domain {domain}: {success_count}/{len(permissions)} policies added"
            )

            # Consider it successful if at least 80% of policies were added
            return success_count >= len(permissions) * 0.8

        except Exception as e:
            self.logger.error(
                f"Failed to define role '{role_name}' for domain {domain}: {e}"
            )
            return False

    def get_available_roles(self, config_file: str = "roles.yaml") -> List[str]:
        """
        Get list of available roles from configuration.

        Args:
            config_file: Name of the configuration file

        Returns:
            List of role names
        """
        try:
            if config_file.endswith(".yaml") or config_file.endswith(".yml"):
                config = self.load_roles_from_yaml(config_file)
                return list(config.get("roles", {}).keys())
            elif config_file.endswith(".csv"):
                policies = self.load_roles_from_csv(config_file)
                roles = set()
                for policy in policies:
                    if len(policy) >= 2:
                        roles.add(policy[1])
                return list(roles)
            else:
                raise ValueError(
                    f"Unsupported configuration file format: {config_file}"
                )

        except Exception as e:
            self.logger.error(f"Failed to get available roles from {config_file}: {e}")
            return []

    def validate_configuration(self, config_file: str = "roles.yaml") -> Dict[str, Any]:
        """
        Validate role configuration file.

        Args:
            config_file: Name of the configuration file

        Returns:
            Dict containing validation results
        """
        try:
            if config_file.endswith(".yaml") or config_file.endswith(".yml"):
                config = self.load_roles_from_yaml(config_file)
                return self._validate_yaml_config(config)
            elif config_file.endswith(".csv"):
                policies = self.load_roles_from_csv(config_file)
                return self._validate_csv_config(policies)
            else:
                return {
                    "valid": False,
                    "error": f"Unsupported file format: {config_file}",
                }

        except Exception as e:
            return {"valid": False, "error": str(e)}

    def validate_yaml_content(self, yaml_content: str) -> Dict[str, Any]:
        """
        Validate role configuration YAML content.

        Args:
            yaml_content: YAML content as a string

        Returns:
            Dict containing validation results
        """
        try:
            config = self.load_roles_from_yaml_content(yaml_content)
            validation_result = self._validate_yaml_config(config)

            # Add additional metadata
            if validation_result["valid"]:
                roles = list(config.get("roles", {}).keys())
                total_permissions = sum(
                    len(actions)
                    for role_config in config.get("roles", {}).values()
                    for actions in role_config.get("permissions", {}).values()
                )
                validation_result["available_roles"] = roles
                validation_result["total_permissions"] = total_permissions

            return validation_result

        except Exception as e:
            return {"valid": False, "error": str(e)}

    def _validate_yaml_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate YAML configuration structure."""
        errors = []
        warnings = []

        if "roles" not in config:
            errors.append("Missing 'roles' section")

        for role_name, role_config in config.get("roles", {}).items():
            if "permissions" not in role_config:
                errors.append(f"Role '{role_name}' missing 'permissions' section")
                continue

            for resource, actions in role_config["permissions"].items():
                if not isinstance(actions, list):
                    errors.append(
                        f"Role '{role_name}' resource '{resource}' actions must be a list"
                    )
                else:
                    for action in actions:
                        if not isinstance(action, str):
                            errors.append(
                                f"Role '{role_name}' resource '{resource}' action must be a string"
                            )

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def _validate_csv_config(self, policies: List[List[str]]) -> Dict[str, Any]:
        """Validate CSV configuration structure."""
        errors = []
        warnings = []

        for i, policy in enumerate(policies):
            if len(policy) < 5:
                errors.append(
                    f"Policy {i+1}: insufficient fields (expected 5, got {len(policy)})"
                )
            elif policy[0] != "p":
                errors.append(f"Policy {i+1}: first field must be 'p'")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


# Global instance
role_config_service = RoleConfigService()
