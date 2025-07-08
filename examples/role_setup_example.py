#!/usr/bin/env python3
"""
Example script demonstrating how to define and use roles in the Custos authorization system.

This script shows:
1. How to define roles with permissions
2. How to assign roles to users
3. How to check authorization
4. How to query user permissions
"""

import requests
import json
from typing import Dict, Any


class CustosClient:
    """Simple client for interacting with the Custos authorization service."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.auth_headers = {"Authorization": "Bearer mock_token"}  # For testing

    def setup_default_roles(self, domain: str) -> Dict[str, Any]:
        """Set up default roles (admin, editor, viewer) for a domain."""
        url = f"{self.base_url}/authorization/setup-default-roles/{domain}"
        response = requests.post(url, headers=self.auth_headers)
        return response.json()

    def define_custom_role(
        self, role_name: str, domain: str, permissions: list
    ) -> Dict[str, Any]:
        """Define a custom role with specific permissions."""
        url = f"{self.base_url}/authorization/define-role"
        payload = {
            "role_type": "custom",
            "role_name": role_name,
            "domain": domain,
            "custom_permissions": permissions,
        }
        response = requests.post(url, json=payload, headers=self.auth_headers)
        return response.json()

    def assign_role(self, user_id: str, role: str, domain: str) -> Dict[str, Any]:
        """Assign a role to a user."""
        url = f"{self.base_url}/authorization/assign-role"
        payload = {"user_id": user_id, "role": role, "domain": domain}
        response = requests.post(url, json=payload, headers=self.auth_headers)
        return response.json()

    def check_authorization(
        self, user_id: str, action: str, resource: str, domain: str
    ) -> Dict[str, Any]:
        """Check if a user is authorized to perform an action on a resource."""
        url = f"{self.base_url}/authorization/authorize"
        payload = {
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "domain": domain,
        }
        response = requests.post(url, json=payload, headers=self.auth_headers)
        return response.json()

    def get_user_permissions(self, user_id: str, domain: str) -> Dict[str, Any]:
        """Get all permissions for a user."""
        url = f"{self.base_url}/authorization/permissions"
        payload = {"user_id": user_id, "domain": domain}
        response = requests.post(url, json=payload, headers=self.auth_headers)
        return response.json()

    def list_roles(self, domain: str) -> Dict[str, Any]:
        """List all roles defined for a domain."""
        url = f"{self.base_url}/authorization/roles/{domain}"
        response = requests.get(url, headers=self.auth_headers)
        return response.json()

    def get_role_permissions(self, domain: str, role_name: str) -> Dict[str, Any]:
        """Get all permissions for a specific role."""
        url = f"{self.base_url}/authorization/roles/{domain}/{role_name}/permissions"
        response = requests.get(url, headers=self.auth_headers)
        return response.json()


def main():
    """Main example demonstrating role setup and usage."""

    # Initialize client
    client = CustosClient()
    domain = "account-123"

    print("🔐 Custos Role Management Example")
    print("=" * 50)

    # Step 1: Set up default roles
    print("\n1️⃣ Setting up default roles...")
    setup_result = client.setup_default_roles(domain)
    print(f"✅ Setup result: {json.dumps(setup_result, indent=2)}")

    # Step 2: Define a custom role
    print("\n2️⃣ Defining a custom 'moderator' role...")
    moderator_permissions = [
        ("users", "read"),
        ("users", "write"),
        ("documents", "read"),
        ("documents", "write"),
        ("comments", "read"),
        ("comments", "write"),
        ("comments", "delete"),
    ]
    custom_role_result = client.define_custom_role(
        "moderator", domain, moderator_permissions
    )
    print(f"✅ Custom role result: {json.dumps(custom_role_result, indent=2)}")

    # Step 3: List all roles
    print("\n3️⃣ Listing all roles in the domain...")
    roles_result = client.list_roles(domain)
    print(f"✅ Roles: {json.dumps(roles_result, indent=2)}")

    # Step 4: Check role permissions
    print("\n4️⃣ Checking permissions for 'admin' role...")
    admin_permissions = client.get_role_permissions(domain, "admin")
    print(f"✅ Admin permissions: {json.dumps(admin_permissions, indent=2)}")

    # Step 5: Assign roles to users
    print("\n5️⃣ Assigning roles to users...")

    # Assign admin role to user1
    user1_id = "auth0|user1"
    admin_assignment = client.assign_role(user1_id, "admin", domain)
    print(f"✅ Admin assignment: {json.dumps(admin_assignment, indent=2)}")

    # Assign editor role to user2
    user2_id = "auth0|user2"
    editor_assignment = client.assign_role(user2_id, "editor", domain)
    print(f"✅ Editor assignment: {json.dumps(editor_assignment, indent=2)}")

    # Assign moderator role to user3
    user3_id = "auth0|user3"
    moderator_assignment = client.assign_role(user3_id, "moderator", domain)
    print(f"✅ Moderator assignment: {json.dumps(moderator_assignment, indent=2)}")

    # Step 6: Test authorization checks
    print("\n6️⃣ Testing authorization checks...")

    # Test admin user permissions
    print(f"\n🔍 Testing admin user ({user1_id}):")
    admin_tests = [
        ("users", "delete"),  # Should be allowed
        ("projects", "create"),  # Should be allowed
        ("settings", "write"),  # Should be allowed
    ]

    for resource, action in admin_tests:
        result = client.check_authorization(user1_id, action, resource, domain)
        status = "✅ ALLOWED" if result["allowed"] else "❌ DENIED"
        print(f"  {action} {resource}: {status}")

    # Test editor user permissions
    print(f"\n🔍 Testing editor user ({user2_id}):")
    editor_tests = [
        ("users", "read"),  # Should be allowed
        ("users", "delete"),  # Should be denied
        ("documents", "write"),  # Should be allowed
        ("settings", "write"),  # Should be denied
    ]

    for resource, action in editor_tests:
        result = client.check_authorization(user2_id, action, resource, domain)
        status = "✅ ALLOWED" if result["allowed"] else "❌ DENIED"
        print(f"  {action} {resource}: {status}")

    # Test moderator user permissions
    print(f"\n🔍 Testing moderator user ({user3_id}):")
    moderator_tests = [
        ("users", "write"),  # Should be allowed
        ("comments", "delete"),  # Should be allowed
        ("projects", "create"),  # Should be denied
        ("settings", "read"),  # Should be denied
    ]

    for resource, action in moderator_tests:
        result = client.check_authorization(user3_id, action, resource, domain)
        status = "✅ ALLOWED" if result["allowed"] else "❌ DENIED"
        print(f"  {action} {resource}: {status}")

    # Step 7: Get user permissions
    print("\n7️⃣ Getting user permissions...")

    for user_id, role in [
        (user1_id, "admin"),
        (user2_id, "editor"),
        (user3_id, "moderator"),
    ]:
        permissions = client.get_user_permissions(user_id, domain)
        print(f"\n👤 {user_id} ({role}):")
        print(f"  Roles: {permissions['roles']}")
        print(f"  Permissions: {permissions['permissions'][:5]}...")  # Show first 5

    print("\n🎉 Example completed successfully!")


if __name__ == "__main__":
    main()
