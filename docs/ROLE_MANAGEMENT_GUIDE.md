# Complete Role Management Guide for Custos

This comprehensive guide covers everything you need to know about defining and managing roles in the Custos authorization system.

## Table of Contents

1. [Overview](#overview)
2. [Core Concepts](#core-concepts)
3. [Quick Start](#quick-start)
4. [API Reference](#api-reference)
5. [Role Types](#role-types)
6. [Usage Examples](#usage-examples)
7. [Best Practices](#best-practices)
8. [Integration Patterns](#integration-patterns)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Topics](#advanced-topics)

---

## Overview

Custos is a centralized authorization service that uses **Casbin** for role-based access control (RBAC) with domain-based multi-tenancy. It answers the critical question:

> *"Is user X allowed to perform action Y on resource Z?"*

### Key Features

- **Domain-Based RBAC**: Roles are scoped to domains (accounts, workspaces, projects)
- **Flexible Role Definition**: Predefined roles + custom roles with granular permissions
- **Multi-Tenant Support**: Complete isolation between domains
- **RESTful API**: Clean HTTP interface for all operations
- **Persistent Storage**: PostgreSQL-backed policy storage

---

## Core Concepts

### 1. Domain-Based RBAC Structure

```
Domain (e.g., account-123)
├── Role: admin
│   ├── users: read, write, delete, create
│   ├── projects: read, write, delete, create
│   └── documents: read, write, delete, create
├── Role: editor
│   ├── users: read
│   ├── projects: read, write, create
│   └── documents: read, write, create
└── Role: viewer
    ├── users: read
    ├── projects: read
    └── documents: read
```

### 2. Permission Format

Permissions follow the pattern: `(role, domain, resource, action)`

**Examples:**
- `(admin, account-123, users, read)` - Admin can read users in account-123
- `(editor, account-123, documents, write)` - Editor can write documents in account-123
- `(viewer, account-123, projects, read)` - Viewer can read projects in account-123

### 3. Two-Step Role Process

**Step 1: Define Role Permissions**
```python
# Define what each role can do
casbin_service.add_policy("admin", "account-123", "users", "read", domain="account-123")
casbin_service.add_policy("admin", "account-123", "users", "write", domain="account-123")
```

**Step 2: Assign Roles to Users**
```python
# Assign roles to specific users
casbin_service.assign_role("auth0|user123", "admin", domain="account-123")
```

---

## Quick Start

### 1. Set Up Default Roles

```bash
# Set up admin, editor, and viewer roles for a domain
curl -X POST "http://localhost:8000/authorization/setup-default-roles/account-123" \
  -H "Authorization: Bearer your-token"
```

### 2. Assign Roles to Users

```bash
# Assign admin role to account owner
curl -X POST "http://localhost:8000/authorization/assign-role" \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "auth0|owner123",
    "role": "admin",
    "domain": "account-123"
  }'
```

### 3. Check Authorization

```bash
# Check if user can delete users
curl -X POST "http://localhost:8000/authorization/authorize" \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "auth0|owner123",
    "action": "delete",
    "resource": "users",
    "domain": "account-123"
  }'
```

### 4. Python Example

```python
from app.services.role_definition_service import role_definition_service
from app.services.casbin_service import casbin_service

# Set up roles for new account
domain = "account-123"
role_definition_service.setup_default_roles(domain)

# Assign roles
casbin_service.assign_role("auth0|owner", "admin", domain)
casbin_service.assign_role("auth0|manager", "editor", domain)
casbin_service.assign_role("auth0|employee", "viewer", domain)

# Check permissions
allowed = casbin_service.authorize("auth0|owner", "delete", "users", domain)
print(f"Can delete users: {allowed}")  # True
```

---

## API Reference

### Role Definition Endpoints

#### Set Up Default Roles
```http
POST /authorization/setup-default-roles/{domain}
```

Creates admin, editor, and viewer roles for a domain.

**Response:**
```json
{
  "domain": "account-123",
  "results": {
    "admin": true,
    "editor": true,
    "viewer": true
  },
  "success_count": 3,
  "total_roles": 3,
  "message": "Default roles setup completed: 3/3 roles created successfully"
}
```

#### Define Custom Role
```http
POST /authorization/define-role
```

**Request Body:**
```json
{
  "role_type": "custom",
  "role_name": "moderator",
  "domain": "account-123",
  "custom_permissions": [
    ["users", "read"],
    ["users", "write"],
    ["comments", "read"],
    ["comments", "write"],
    ["comments", "delete"]
  ]
}
```

**Response:**
```json
{
  "success": true,
  "role_name": "moderator",
  "domain": "account-123",
  "role_type": "custom",
  "message": "Role 'moderator' successfully defined in domain 'account-123'"
}
```

### Role Management Endpoints

#### List All Roles
```http
GET /authorization/roles/{domain}
```

**Response:**
```json
{
  "domain": "account-123",
  "roles": ["admin", "editor", "viewer", "moderator"],
  "count": 4
}
```

#### Get Role Permissions
```http
GET /authorization/roles/{domain}/{role_name}/permissions
```

**Response:**
```json
{
  "role_name": "admin",
  "domain": "account-123",
  "permissions": [
    "users:read",
    "users:write",
    "users:delete",
    "users:create",
    "projects:read",
    "projects:write",
    "projects:delete",
    "projects:create"
  ],
  "count": 8
}
```

#### Assign Role to User
```http
POST /authorization/assign-role
```

**Request Body:**
```json
{
  "user_id": "auth0|user123",
  "role": "admin",
  "domain": "account-123"
}
```

**Response:**
```json
{
  "success": true,
  "user_id": "auth0|user123",
  "role": "admin",
  "domain": "account-123",
  "resource": null,
  "message": "Role 'admin' successfully assigned to user 'auth0|user123'"
}
```

#### Remove Role from User
```http
DELETE /authorization/remove-role
```

**Request Body:**
```json
{
  "user_id": "auth0|user123",
  "role": "admin",
  "domain": "account-123"
}
```

### Authorization Endpoints

#### Check Authorization
```http
POST /authorization/authorize
```

**Request Body:**
```json
{
  "user_id": "auth0|user123",
  "action": "read",
  "resource": "users",
  "domain": "account-123"
}
```

**Response:**
```json
{
  "allowed": true,
  "user_id": "auth0|user123",
  "action": "read",
  "resource": "users",
  "domain": "account-123",
  "resource_id": null,
  "reason": null
}
```

#### Get User Permissions
```http
POST /authorization/permissions
```

**Request Body:**
```json
{
  "user_id": "auth0|user123",
  "domain": "account-123"
}
```

**Response:**
```json
{
  "user_id": "auth0|user123",
  "domain": "account-123",
  "permissions": [
    "users:read",
    "users:write",
    "users:delete",
    "users:create",
    "projects:read",
    "projects:write"
  ],
  "roles": ["admin"]
}
```

---

## Role Types

### 1. Admin Role
**Full system access within the domain**

**Permissions:**
- User management: read, write, delete, create
- Project management: read, write, delete, create
- Document management: read, write, delete, create
- Role management: read, write, delete, create
- Settings: read, write

**Use Case:** Account owners, system administrators

### 2. Editor Role
**Content creation and editing**

**Permissions:**
- User management: read only
- Project management: read, write, create
- Document management: read, write, create
- Settings: read only

**Use Case:** Team leads, content managers, senior developers

### 3. Viewer Role
**Read-only access**

**Permissions:**
- User management: read only
- Project management: read only
- Document management: read only
- Settings: read only

**Use Case:** Stakeholders, junior team members, external collaborators

### 4. Custom Roles
**Flexible permission sets**

**Examples:**
- **Moderator**: User management + comment moderation
- **Support**: User read + ticket management
- **Analyst**: Read access to all data + export permissions
- **Guest**: Limited read access to specific resources

---

## Usage Examples

### 1. Setting Up a New Account

```python
from custos_client import CustosClient

client = CustosClient("http://localhost:8000")
domain = "account-456"

# Set up default roles
result = client.setup_default_roles(domain)
print(f"Roles created: {result['success_count']}/{result['total_roles']}")

# Assign admin to account owner
client.assign_role("auth0|owner123", "admin", domain)

# Assign editor to team lead
client.assign_role("auth0|lead456", "editor", domain)

# Assign viewer to stakeholders
client.assign_role("auth0|stakeholder789", "viewer", domain)
```

### 2. Creating a Support Team

```python
# Define support role with ticket management permissions
support_permissions = [
    ("users", "read"),
    ("tickets", "read"),
    ("tickets", "write"),
    ("tickets", "create"),
    ("tickets", "delete")
]

client.define_custom_role("support", domain, support_permissions)

# Assign support role to team members
support_team = ["auth0|support1", "auth0|support2", "auth0|support3"]
for user_id in support_team:
    client.assign_role(user_id, "support", domain)
```

### 3. Project-Specific Permissions

```python
# Create project-specific domain
project_domain = f"project-{project_id}"

# Define project roles
client.define_custom_role("project-admin", project_domain, [
    ("tasks", "read"), ("tasks", "write"), ("tasks", "delete"),
    ("milestones", "read"), ("milestones", "write"), ("milestones", "delete"),
    ("team", "read"), ("team", "write")
])

client.define_custom_role("project-member", project_domain, [
    ("tasks", "read"), ("tasks", "write"),
    ("milestones", "read"),
    ("team", "read")
])

# Assign project roles
client.assign_role("auth0|pm123", "project-admin", project_domain)
client.assign_role("auth0|dev456", "project-member", project_domain)
```

### 4. Temporary Access Management

```python
# Grant temporary admin access for maintenance
client.assign_role("auth0|maintenance", "admin", domain)

# Perform maintenance tasks
# ... maintenance operations ...

# Remove temporary access
client.remove_role("auth0|maintenance", "admin", domain)
```

### 5. Bulk Role Assignment

```python
# Team role mapping
team_roles = {
    "team-lead": ["admin"],
    "senior-dev": ["editor"],
    "junior-dev": ["viewer"],
    "qa-engineer": ["editor"],
    "designer": ["editor"]
}

# Assign roles based on team member data
for user_id, role in team_members.items():
    if role in team_roles:
        for assigned_role in team_roles[role]:
            client.assign_role(user_id, assigned_role, domain)
```

---

## Best Practices

### 1. Role Design Principles

**Principle of Least Privilege**
- Give users only the permissions they need
- Start with restrictive roles and add permissions as needed
- Regularly review and audit role assignments

**Role Hierarchy**
- Design roles that reflect your business structure
- Use consistent naming conventions
- Document role purposes and responsibilities

**Granular Permissions**
- Break down permissions by resource and action
- Consider resource-specific roles for complex systems
- Use custom roles for specialized access patterns

### 2. Domain Organization

**Account-Based Domains**
```python
domain = f"account-{account_id}"
```
Use for multi-tenant applications where each account is isolated.

**Workspace-Based Domains**
```python
domain = f"workspace-{workspace_id}"
```
Use for collaborative features within accounts.

**Project-Based Domains**
```python
domain = f"project-{project_id}"
```
Use for project-specific permissions and team management.

### 3. Security Considerations

**Regular Audits**
- Review role assignments quarterly
- Remove unused roles and permissions
- Monitor for privilege escalation

**Temporary Access**
- Use time-limited role assignments
- Implement approval workflows for elevated access
- Log all role changes for audit trails

**Role Inheritance**
- Be careful with role hierarchies
- Avoid deep nesting that could lead to privilege escalation
- Test role combinations thoroughly

### 4. Performance Optimization

**Efficient Authorization Checks**
```python
# Cache user permissions for frequently accessed data
user_permissions = cache.get(f"permissions:{user_id}:{domain}")
if not user_permissions:
    user_permissions = client.get_user_permissions(user_id, domain)
    cache.set(f"permissions:{user_id}:{domain}", user_permissions, ttl=300)
```

**Batch Operations**
```python
# Use batch endpoints when available
# Group role assignments by domain
# Minimize API calls for bulk operations
```

---

## Integration Patterns

### 1. FastAPI Integration

```python
from fastapi import Depends, HTTPException
from custos_client import CustosClient

async def require_permission(
    user_id: str,
    action: str,
    resource: str,
    domain: str,
    client: CustosClient = Depends(get_custos_client)
):
    result = client.check_authorization(user_id, action, resource, domain)
    if not result["allowed"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    return True

@app.get("/users/{user_id}")
async def get_user(
    user_id: str,
    current_user: str = Depends(get_current_user),
    domain: str = Depends(get_domain)
):
    await require_permission(current_user, "read", "users", domain)
    # ... fetch and return user data

@app.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: str = Depends(get_current_user),
    domain: str = Depends(get_domain)
):
    await require_permission(current_user, "delete", "users", domain)
    # ... delete user logic
```

### 2. Frontend Integration

```javascript
// Permission checking utility
class PermissionManager {
    constructor(baseUrl, token) {
        this.baseUrl = baseUrl;
        this.token = token;
    }

    async checkPermission(action, resource, domain) {
        const response = await fetch(`${this.baseUrl}/authorization/authorize`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: this.currentUser.id,
                action: action,
                resource: resource,
                domain: domain
            })
        });
        
        const result = await response.json();
        return result.allowed;
    }

    async getUserPermissions(domain) {
        const response = await fetch(`${this.baseUrl}/authorization/permissions`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: this.currentUser.id,
                domain: domain
            })
        });
        
        return await response.json();
    }
}

// Usage in React components
function UserManagement({ domain }) {
    const [permissions, setPermissions] = useState({});
    const [canDeleteUsers, setCanDeleteUsers] = useState(false);

    useEffect(() => {
        async function loadPermissions() {
            const permManager = new PermissionManager(API_BASE_URL, token);
            const userPerms = await permManager.getUserPermissions(domain);
            setPermissions(userPerms);
            
            const canDelete = await permManager.checkPermission('delete', 'users', domain);
            setCanDeleteUsers(canDelete);
        }
        
        loadPermissions();
    }, [domain]);

    return (
        <div>
            <h2>User Management</h2>
            {canDeleteUsers && (
                <button onClick={handleDeleteUser}>Delete User</button>
            )}
            {permissions.permissions?.includes('users:write') && (
                <button onClick={handleEditUser}>Edit User</button>
            )}
        </div>
    );
}
```

### 3. Middleware Integration

```python
# Django middleware example
class CustosMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.custos_client = CustosClient(CUSTOS_BASE_URL)

    def __call__(self, request):
        # Extract user and domain from request
        user_id = request.user.auth0_id
        domain = request.session.get('current_domain')
        
        # Add permission checking to request
        request.check_permission = lambda action, resource: self.check_permission(
            user_id, action, resource, domain
        )
        
        response = self.get_response(request)
        return response

    def check_permission(self, user_id, action, resource, domain):
        try:
            result = self.custos_client.check_authorization(user_id, action, resource, domain)
            return result.get('allowed', False)
        except Exception:
            return False

# Usage in views
def delete_user_view(request, user_id):
    if not request.check_permission('delete', 'users'):
        return HttpResponseForbidden("Permission denied")
    
    # Delete user logic
    pass
```

---

## Troubleshooting

### Common Issues

#### 1. Role Not Found
**Symptoms:** 400 error when assigning roles
**Solutions:**
- Ensure the role is defined before assigning it
- Check the domain matches exactly
- Use the role listing endpoint to verify available roles

```python
# Debug: List available roles
roles = client.list_roles(domain)
print(f"Available roles: {roles['roles']}")
```

#### 2. Permission Denied
**Symptoms:** Authorization checks return false
**Solutions:**
- Verify the user has the correct role
- Check if the role has the required permissions
- Ensure the domain matches

```python
# Debug: Check user's current roles
permissions = client.get_user_permissions(user_id, domain)
print(f"User roles: {permissions['roles']}")

# Debug: Check role permissions
role_perms = client.get_role_permissions(domain, "admin")
print(f"Admin permissions: {role_perms['permissions']}")
```

#### 3. Policy Conflicts
**Symptoms:** Unexpected authorization results
**Solutions:**
- Review existing policies for conflicts
- Use the role listing endpoints to debug
- Check for duplicate role assignments

```python
# Debug: Check all policies for a role
policies = casbin_service.enforcer.get_filtered_policy(0, "admin")
print(f"Admin policies: {policies}")
```

### Debug Commands

```python
# Comprehensive debugging
def debug_user_permissions(user_id, domain):
    print(f"=== Debugging permissions for {user_id} in {domain} ===")
    
    # Check user roles
    roles = casbin_service.get_user_roles(user_id, domain)
    print(f"User roles: {roles}")
    
    # Check user permissions
    permissions = casbin_service.get_user_permissions(user_id, domain)
    print(f"User permissions: {permissions}")
    
    # Check specific authorization
    test_cases = [
        ("read", "users"),
        ("write", "users"),
        ("delete", "users"),
        ("read", "projects"),
        ("write", "projects")
    ]
    
    for action, resource in test_cases:
        allowed = casbin_service.authorize(user_id, action, resource, domain)
        print(f"  {action} {resource}: {'✅' if allowed else '❌'}")

# Usage
debug_user_permissions("auth0|user123", "account-123")
```

### Error Handling

```python
# Robust error handling for authorization checks
def safe_authorize(user_id, action, resource, domain):
    try:
        return casbin_service.authorize(user_id, action, resource, domain)
    except Exception as e:
        logger.error(f"Authorization check failed: {e}")
        # Default to deny for security
        return False

# Usage in production
if safe_authorize(user_id, "delete", "users", domain):
    # Proceed with deletion
    pass
else:
    # Handle permission denied
    raise HTTPException(status_code=403, detail="Permission denied")
```

---

## Advanced Topics

### 1. Role Inheritance

While Custos doesn't support built-in role inheritance, you can implement it:

```python
class RoleHierarchy:
    def __init__(self):
        self.hierarchy = {
            "admin": ["editor", "viewer"],
            "editor": ["viewer"],
            "viewer": []
        }
    
    def get_inherited_roles(self, role):
        """Get all roles that inherit from the given role."""
        inherited = []
        for parent, children in self.hierarchy.items():
            if role in children:
                inherited.append(parent)
        return inherited
    
    def assign_with_inheritance(self, user_id, role, domain):
        """Assign role and all inherited roles."""
        roles_to_assign = [role] + self.get_inherited_roles(role)
        for r in roles_to_assign:
            casbin_service.assign_role(user_id, r, domain)
```

### 2. Time-Based Permissions

Implement temporary role assignments:

```python
import time
from datetime import datetime, timedelta

class TemporaryRoleManager:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def assign_temporary_role(self, user_id, role, domain, duration_hours=24):
        """Assign a role that expires after the specified duration."""
        expiry = datetime.now() + timedelta(hours=duration_hours)
        
        # Assign the role
        casbin_service.assign_role(user_id, role, domain)
        
        # Schedule removal
        self.redis.setex(
            f"temp_role:{user_id}:{role}:{domain}",
            int(duration_hours * 3600),
            expiry.isoformat()
        )
    
    def cleanup_expired_roles(self):
        """Remove expired temporary roles."""
        pattern = "temp_role:*"
        for key in self.redis.scan_iter(match=pattern):
            if not self.redis.exists(key):
                # Key has expired, remove the role
                parts = key.split(":")
                user_id, role, domain = parts[1], parts[2], parts[3]
                casbin_service.remove_role(user_id, role, domain)
                self.redis.delete(key)
```

### 3. Dynamic Permission Loading

Load permissions from external sources:

```python
class DynamicPermissionLoader:
    def __init__(self, config_source):
        self.config_source = config_source
    
    def load_role_permissions(self, role_name, domain):
        """Load role permissions from external configuration."""
        config = self.config_source.get_role_config(role_name, domain)
        
        for resource, actions in config['permissions'].items():
            for action in actions:
                casbin_service.add_policy(role_name, resource, action, domain=domain)
    
    def refresh_all_roles(self, domain):
        """Refresh all role permissions from configuration."""
        roles = self.config_source.get_all_roles(domain)
        
        for role_name in roles:
            # Remove existing policies for this role
            policies = casbin_service.enforcer.get_filtered_policy(0, role_name)
            for policy in policies:
                if len(policy) >= 4 and policy[1] == domain:
                    casbin_service.enforcer.remove_policy(policy)
            
            # Load fresh permissions
            self.load_role_permissions(role_name, domain)
```

### 4. Audit Logging

Comprehensive audit trail for role changes:

```python
import logging
from datetime import datetime

class RoleAuditLogger:
    def __init__(self):
        self.audit_logger = logging.getLogger('role_audit')
    
    def log_role_assignment(self, user_id, role, domain, assigned_by):
        """Log role assignment."""
        self.audit_logger.info(
            f"ROLE_ASSIGNED: user={user_id}, role={role}, domain={domain}, "
            f"assigned_by={assigned_by}, timestamp={datetime.now().isoformat()}"
        )
    
    def log_role_removal(self, user_id, role, domain, removed_by):
        """Log role removal."""
        self.audit_logger.info(
            f"ROLE_REMOVED: user={user_id}, role={role}, domain={domain}, "
            f"removed_by={removed_by}, timestamp={datetime.now().isoformat()}"
        )
    
    def log_permission_check(self, user_id, action, resource, domain, allowed):
        """Log permission checks."""
        self.audit_logger.debug(
            f"PERMISSION_CHECK: user={user_id}, action={action}, resource={resource}, "
            f"domain={domain}, allowed={allowed}, timestamp={datetime.now().isoformat()}"
        )

# Usage with existing services
class AuditedCasbinService(CasbinService):
    def __init__(self):
        super().__init__()
        self.audit_logger = RoleAuditLogger()
    
    def assign_role(self, user_id, role, domain, assigned_by=None):
        result = super().assign_role(user_id, role, domain)
        if result and assigned_by:
            self.audit_logger.log_role_assignment(user_id, role, domain, assigned_by)
        return result
    
    def authorize(self, user_id, action, resource, domain):
        result = super().authorize(user_id, action, resource, domain)
        self.audit_logger.log_permission_check(user_id, action, resource, domain, result)
        return result
```

---

## Conclusion

This guide covers the complete role management system in Custos. The key takeaways are:

1. **Start Simple**: Use the default roles (admin, editor, viewer) for most use cases
2. **Design Carefully**: Plan your role structure before implementation
3. **Test Thoroughly**: Verify permissions work as expected
4. **Monitor Continuously**: Regular audits and monitoring are essential
5. **Document Everything**: Keep clear documentation of role purposes and assignments

The system is designed to be flexible and scalable, supporting everything from simple applications to complex multi-tenant systems with sophisticated permission requirements.

For additional support or questions, refer to the API documentation or contact the development team. 