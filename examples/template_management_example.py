"""
Example: Managing Role Templates Across Multiple Domains

This example demonstrates how to use the role template system to efficiently
manage roles and permissions across multiple domains (tenants).
"""

import requests
import json
from typing import List, Dict


class TemplateManagementExample:
    """Example class demonstrating template management workflows"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.auth_headers = {
            "Authorization": "Bearer your-jwt-token-here",
            "Content-Type": "application/json",
        }

    def create_standard_template(self) -> bool:
        """Create a standard roles template"""
        template_config = {
            "roles": {
                "admin": {
                    "description": "Full system administrator",
                    "permissions": {
                        "users": ["read", "write", "delete", "create"],
                        "projects": ["read", "write", "delete", "create"],
                        "documents": ["read", "write", "delete", "create"],
                        "reports": ["read", "write", "delete", "create"],
                    },
                },
                "editor": {
                    "description": "Content editor",
                    "permissions": {
                        "users": ["read"],
                        "projects": ["read", "write", "create"],
                        "documents": ["read", "write", "create"],
                        "reports": ["read", "write"],
                    },
                },
                "viewer": {
                    "description": "Read-only user",
                    "permissions": {
                        "users": ["read"],
                        "projects": ["read"],
                        "documents": ["read"],
                        "reports": ["read"],
                    },
                },
            }
        }

        response = requests.post(
            f"{self.base_url}/authorization/templates",
            headers=self.auth_headers,
            json={"template_name": "standard-roles", "role_config": template_config},
        )

        if response.status_code == 200:
            print("✅ Standard template created successfully")
            return True
        else:
            print(f"❌ Failed to create template: {response.text}")
            return False

    def apply_template_to_domains(self, template_name: str, domains: List[str]) -> Dict:
        """Apply a template to multiple domains"""
        response = requests.post(
            f"{self.base_url}/authorization/templates/{template_name}/apply-multiple",
            headers=self.auth_headers,
            json={"domains": domains, "overwrite_existing": True},
        )

        if response.status_code == 200:
            result = response.json()
            print(
                f"✅ Template applied to {result['success_count']}/{result['total_domains']} domains"
            )
            return result
        else:
            print(f"❌ Failed to apply template: {response.text}")
            return {}

    def add_permission_to_template(
        self, template_name: str, role_name: str, resource: str, action: str
    ) -> bool:
        """Add a new permission to a role in a template"""
        response = requests.post(
            f"{self.base_url}/authorization/templates/{template_name}/add-permission",
            headers=self.auth_headers,
            json={"role_name": role_name, "resource": resource, "action": action},
        )

        if response.status_code == 200:
            print(f"✅ Permission {action}:{resource} added to role {role_name}")
            return True
        else:
            print(f"❌ Failed to add permission: {response.text}")
            return False

    def update_template_and_apply(
        self, template_name: str, updated_config: Dict, domains: List[str]
    ) -> Dict:
        """Update a template and apply it to multiple domains"""
        response = requests.post(
            f"{self.base_url}/authorization/templates/{template_name}/update-and-apply",
            headers=self.auth_headers,
            json={
                "updated_config": updated_config,
                "domains": domains,
                "overwrite_existing": True,
            },
        )

        if response.status_code == 200:
            result = response.json()
            print(
                f"✅ Template updated and applied to {result['success_count']}/{result['total_domains']} domains"
            )
            return result
        else:
            print(f"❌ Failed to update and apply template: {response.text}")
            return {}

    def list_templates(self) -> List[str]:
        """List all available templates"""
        response = requests.get(
            f"{self.base_url}/authorization/templates", headers=self.auth_headers
        )

        if response.status_code == 200:
            result = response.json()
            print(f"📋 Available templates: {result['templates']}")
            return result["templates"]
        else:
            print(f"❌ Failed to list templates: {response.text}")
            return []

    def get_template(self, template_name: str) -> Dict:
        """Get a specific template"""
        response = requests.get(
            f"{self.base_url}/authorization/templates/{template_name}",
            headers=self.auth_headers,
        )

        if response.status_code == 200:
            result = response.json()
            print(f"📄 Template '{template_name}' loaded")
            return result
        else:
            print(f"❌ Failed to get template: {response.text}")
            return {}


def demonstrate_workflow():
    """Demonstrate the complete template management workflow"""

    example = TemplateManagementExample()

    print("🚀 Starting Template Management Workflow")
    print("=" * 50)

    # Step 1: Create a standard template
    print("\n1️⃣ Creating standard roles template...")
    example.create_standard_template()

    # Step 2: List available templates
    print("\n2️⃣ Listing available templates...")
    templates = example.list_templates()

    # Step 3: Apply template to multiple domains
    print("\n3️⃣ Applying template to multiple domains...")
    domains = [f"tenant-{i}" for i in range(1, 201)]  # 200 domains
    example.apply_template_to_domains("standard-roles", domains)

    # Step 4: Add a new permission to the template
    print("\n4️⃣ Adding new permission to template...")
    example.add_permission_to_template("standard-roles", "admin", "analytics", "read")
    example.add_permission_to_template("standard-roles", "editor", "analytics", "read")

    # Step 5: Update template and apply to all domains
    print("\n5️⃣ Updating template and applying to all domains...")

    # Get current template
    current_template = example.get_template("standard-roles")
    if current_template:
        updated_config = current_template["config"]

        # Add new resource permissions
        if "roles" in updated_config and "admin" in updated_config["roles"]:
            if "permissions" not in updated_config["roles"]["admin"]:
                updated_config["roles"]["admin"]["permissions"] = {}

            updated_config["roles"]["admin"]["permissions"]["analytics"] = [
                "read",
                "write",
            ]

        # Apply updated template
        example.update_template_and_apply("standard-roles", updated_config, domains)

    print("\n✅ Template management workflow completed!")


def demonstrate_scenario_1():
    """Scenario 1: Adding a new permission to all domains"""
    print("\n" + "=" * 60)
    print("📋 SCENARIO 1: Adding 'reports:export' permission to admin role")
    print("=" * 60)

    example = TemplateManagementExample()

    # Add the new permission to the template
    success = example.add_permission_to_template(
        "standard-roles", "admin", "reports", "export"
    )

    if success:
        # Apply to all 200 domains
        domains = [f"tenant-{i}" for i in range(1, 201)]
        example.update_template_and_apply("standard-roles", {}, domains)

    print("✅ New permission added to all domains in one operation!")


def demonstrate_scenario_2():
    """Scenario 2: Creating a new role and applying it"""
    print("\n" + "=" * 60)
    print("📋 SCENARIO 2: Creating a new 'analyst' role")
    print("=" * 60)

    example = TemplateManagementExample()

    # Get current template
    current_template = example.get_template("standard-roles")
    if current_template:
        updated_config = current_template["config"]

        # Add new analyst role
        if "roles" not in updated_config:
            updated_config["roles"] = {}

        updated_config["roles"]["analyst"] = {
            "description": "Data analyst with reporting access",
            "permissions": {
                "reports": ["read", "write", "export"],
                "analytics": ["read", "write"],
                "documents": ["read"],
                "projects": ["read"],
            },
        }

        # Apply to all domains
        domains = [f"tenant-{i}" for i in range(1, 201)]
        example.update_template_and_apply("standard-roles", updated_config, domains)

    print("✅ New analyst role created and applied to all domains!")


if __name__ == "__main__":
    # Run the complete workflow
    demonstrate_workflow()

    # Run specific scenarios
    demonstrate_scenario_1()
    demonstrate_scenario_2()

    print("\n🎉 All examples completed!")
    print("\nKey Benefits:")
    print("• Single template definition for all domains")
    print("• Bulk operations across multiple domains")
    print("• Easy permission updates without touching each domain")
    print("• Consistent role structure across tenants")
    print("• Version control for role templates")
