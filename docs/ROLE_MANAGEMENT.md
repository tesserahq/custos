# Role Management in Custos

This document explains how to define and manage roles in the Custos authorization system.

## Overview

Custos uses **Casbin** for role-based access control (RBAC) with domain-based multi-tenancy. Roles are defined by:

1. **Role Permissions**: What actions each role can perform on what resources
2. **Role Assignments**: Which users have which roles in which domains

## Role Structure

### Domain-Based RBAC
- **Domain**: Multi-tenant scope (e.g., `account-123`, `workspace-456`)
- **Role**: Named permission set (e.g., `admin`, `editor`, `viewer`)
- **User**: Individual user identified by Auth0 sub (e.g., `auth0|user123`)

### Permission Format
Permissions follow the pattern: `(role, domain, resource, action)`

Examples:
- `(admin, account-123, users, read)` - Admin can read users in account-123
- `(editor, account-123, documents, write)` - Editor can write documents in account-123

## Default Roles

The system comes with three predefined roles:

### 1. Admin Role
**Full system access within the domain**
- User management: read, write, delete, create
- Project management: read, write, delete, create
- Document management: read, write, delete, create
- Role management: read, write, delete, create
- Settings: read, write

### 2. Editor Role
**Content creation and editing**
- User management: read only
- Project management: read, write, create
- Document management: read, write, create
- Settings: read only

### 3. Viewer Role
**Read-only access**
- User management: read only
- Project management: read only
- Document management: read only
- Settings: read only

## API Endpoints

### Define Roles

#### Set up Default Roles
```http
POST /authorization/setup-default-roles/{domain}
```

Sets up admin, editor, and viewer roles for a domain.

**Example:**
```bash
curl -X POST "http://localhost:8000/authorization/setup-default-roles/account-123" \
  -H "Authorization: Bearer your-token"
```

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

### List Roles

#### Get All Roles in Domain
```http
GET /authorization/roles/{domain}
```

**Example:**
```bash
curl "http://localhost:8000/authorization/roles/account-123" \
  -H "Authorization: Bearer your-token"
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

**Example:**
```bash
curl "http://localhost:8000/authorization/roles/account-123/admin/permissions" \
  -H "Authorization: Bearer your-token"
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

### Assign Roles

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

### Check Authorization

#### Authorize User Action
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

### Get User Permissions

#### Get User Roles and Permissions
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

## Usage Examples

### 1. Setting Up a New Domain

```python
from custos_client import CustosClient

client = CustosClient("http://localhost:8000")
domain = "account-456"

# Set up default roles
result = client.setup_default_roles(domain)
print(f"Roles created: {result['success_count']}/{result['total_roles']}")
```

### 2. Creating a Custom Role

```python
# Define a "support" role with limited permissions
support_permissions = [
    ("users", "read"),
    ("tickets", "read"),
    ("tickets", "write"),
    ("tickets", "create")
]

result = client.define_custom_role("support", domain, support_permissions)
print(f"Support role created: {result['success']}")
```

### 3. Assigning Roles to Users

```python
# Assign admin role to account owner
client.assign_role("auth0|owner123", "admin", domain)

# Assign editor role to team lead
client.assign_role("auth0|lead456", "editor", domain)

# Assign support role to support staff
client.assign_role("auth0|support789", "support", domain)
```

### 4. Checking Authorization

```python
# Check if user can delete users
result = client.check_authorization("auth0|user123", "delete", "users", domain)
if result["allowed"]:
    print("User can delete users")
else:
    print("User cannot delete users")
```

## Best Practices

### 1. Role Design
- **Principle of Least Privilege**: Give users only the permissions they need
- **Role Hierarchy**: Design roles that make sense for your business
- **Consistent Naming**: Use clear, descriptive role names

### 2. Domain Organization
- **Account-Based**: Use account IDs as domains for multi-tenant applications
- **Workspace-Based**: Use workspace IDs for collaborative features
- **Project-Based**: Use project IDs for project-specific permissions

### 3. Permission Granularity
- **Resource-Level**: `users`, `projects`, `documents`
- **Action-Level**: `read`, `write`, `delete`, `create`
- **Instance-Level**: `users:123`, `projects:456` (if needed)

### 4. Security Considerations
- **Regular Audits**: Review role assignments periodically
- **Temporary Roles**: Consider time-limited role assignments
- **Role Inheritance**: Be careful with role hierarchies to avoid privilege escalation

## Common Patterns

### 1. Team-Based Access
```python
# Assign team roles
team_roles = {
    "team-lead": ["admin"],
    "senior-dev": ["editor"],
    "junior-dev": ["viewer"],
    "qa-engineer": ["editor"]
}

for user_id, roles in team_members.items():
    for role in roles:
        client.assign_role(user_id, role, domain)
```

### 2. Project-Specific Permissions
```python
# Create project-specific roles
project_domain = f"project-{project_id}"
client.define_custom_role("project-admin", project_domain, [
    ("tasks", "read"), ("tasks", "write"), ("tasks", "delete"),
    ("milestones", "read"), ("milestones", "write")
])
```

### 3. Temporary Access
```python
# Grant temporary admin access
client.assign_role(user_id, "admin", domain)

# Later, remove the role
client.remove_role(user_id, "admin", domain)
```

## Troubleshooting

### Common Issues

1. **Role Not Found**
   - Ensure the role is defined before assigning it
   - Check the domain matches exactly

2. **Permission Denied**
   - Verify the user has the correct role
   - Check if the role has the required permissions
   - Ensure the domain matches

3. **Policy Conflicts**
   - Review existing policies for conflicts
   - Use the role listing endpoints to debug

### Debug Commands

```python
# List all roles in domain
roles = client.list_roles(domain)
print(f"Available roles: {roles['roles']}")

# Check user's current roles
permissions = client.get_user_permissions(user_id, domain)
print(f"User roles: {permissions['roles']}")

# Check role permissions
role_perms = client.get_role_permissions(domain, "admin")
print(f"Admin permissions: {role_perms['permissions']}")
```

## Integration Examples

### FastAPI Integration
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
```

### Frontend Integration
```javascript
// Check permissions before showing UI elements
async function checkPermission(action, resource) {
    const response = await fetch('/authorization/authorize', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
            user_id: currentUser.id,
            action: action,
            resource: resource,
            domain: currentDomain
        })
    });
    
    const result = await response.json();
    return result.allowed;
}

// Show/hide UI based on permissions
if (await checkPermission('write', 'users')) {
    showEditButton();
}
``` 