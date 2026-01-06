# Quick Setup Guide

## Initial System Administrator Setup

This guide provides a quick overview of how to set up the first system administrator in Custos.

## Prerequisites

1. **Database**: PostgreSQL database is running and accessible
2. **User**: A user exists in the database with a valid email address
3. **Application**: Custos application is running

## Quick Setup Steps

### 1. Set Environment Variable

You can specify one or more email addresses separated by commas:

```bash
export SUPER_USER_EMAIL="admin1@example.com,admin2@example.com"
```

For a single admin, use just one email:

```bash
export SUPER_USER_EMAIL="your-admin@example.com"
```

### 2. Call Setup Endpoint

```bash
curl -X POST http://localhost:8000/system/setup
```

### 3. Verify Setup

The response should look like:

```json
{
    "success": true,
    "roles_created": 3,
    "roles": [
        {
            "name": "Custos Admin",
            "identifier": "custos-admin",
            "description": "RBAC admin role with full permissions to manage roles and permissions",
            "id": "88da471a-38b8-42e1-aace-1d560957d5ef",
            "created_at": "2025-12-27T16:15:44.507455",
            "updated_at": "2025-12-27T16:15:44.507459"
        },
        {
            "name": "Identies Admin",
            "identifier": "identies-admin",
            "description": "Identies admin role with full permissions to manage Service accounts and more",
            "id": "16bb20cc-a697-4264-8937-b77513cbfeb9",
            "created_at": "2025-12-27T16:15:44.555450",
            "updated_at": "2025-12-27T16:15:44.555454"
        },
        {
            "name": "Orcha Admin",
            "identifier": "orcha-admin",
            "description": "Orcha admin role with full permissions to manage Orcha and more",
            "id": "2da8a0ef-cbf5-4143-99c8-e5bd81ac1ad9",
            "created_at": "2026-01-01T22:29:49.442657",
            "updated_at": "2026-01-01T22:29:49.442661"
        }
    ],
    "message": "Successfully imported 3 role(s) from configuration"
}
```

## What Happens During Setup

When you call the `/system/setup` endpoint, the following process occurs:

1. **Environment Validation**: Verifies that `SUPER_USER_EMAIL` environment variable is set and contains at least one email address

2. **Configuration Loading**: Loads role definitions from the JSON configuration file (`app/config/default_roles.json` by default). This file contains predefined roles with their associated permissions, such as:
   - **Custos Admin**: Full permissions to manage roles, bindings, memberships, and permissions within Custos
   - **Identies Admin**: Full permissions to manage service accounts, API keys, access rules, and users in the Identies service
   - **Orcha Admin**: Full permissions to manage Orcha-related resources
   - And any other roles defined in the configuration

3. **Role Creation**: Creates all roles defined in the configuration file in the database using `CreateRolesBatchCommand`. Each role includes:
   - Role name and identifier
   - Description
   - Associated permissions (object-action pairs)

4. **Policy Binding**: For each created role, creates Casbin policies that bind the role's permissions to the global domain (`*`). This is done via `SyncRolePolicyCommand`, which:
   - Converts each permission (object-action pair) into a Casbin policy
   - Stores the policies in the database with domain `*` for global access

5. **Super User Assignment**: Assigns all created roles to each super user specified in `SUPER_USER_EMAIL`:
   - Looks up each user by email address in the database
   - Creates role bindings for each user-role combination using `CreateBindingCommand`
   - All assignments are made in the global domain (`*`), giving super users access across all domains

After this process completes, the specified super users will have all the predefined roles assigned to them with global domain access, enabling them to manage the authorization system and other services according to the permissions defined in the configuration.

## What Super Users Can Do After Setup

Once setup is complete, the super users specified in `SUPER_USER_EMAIL` will have access to all the roles defined in the configuration file. These typically include:

- ✅ **Custos Administration**: Create and manage roles, permissions, bindings, and memberships
- ✅ **Identies Administration**: Manage service accounts, API keys, access rules, and users
- ✅ **Orcha Administration**: Manage Orcha-related resources
- ✅ **Global Domain Access**: All roles are assigned in the global domain (`*`), providing access across all domains
- ✅ **Role Assignment**: Assign roles to other users throughout the system

The specific capabilities depend on which roles are defined in the `default_roles.json` configuration file.

## Common Issues

| Issue                           | Solution                              |
| ------------------------------- | ------------------------------------- |
| `SUPER_USER_EMAIL` not set      | Set the environment variable          |
| User not found                  | Ensure user exists in database        |
| Database connection error       | Check database connectivity           |
| Role assignment fails           | Check Casbin configuration            |

## Next Steps

After setup, you can:

1. Create additional roles using the authorization endpoints
2. Set up service accounts for API access
3. Configure domain-specific permissions
4. Assign roles to other users

