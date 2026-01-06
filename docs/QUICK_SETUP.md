# Quick Setup Guide

## Initial System Administrator Setup

This guide provides a quick overview of how to set up the first system administrator in Custos.

## Prerequisites

1. **Database**: PostgreSQL database is running and accessible
2. **User**: A user exists in the database with a valid email address
3. **Application**: Custos application is running

## Quick Setup Steps

### 1. Set Environment Variable

```bash
export SUPER_USER_EMAIL="your-admin@example.com"
```

### 2. Call Setup Endpoint

```bash
curl -X POST http://localhost:8000/setup
```

### 3. Verify Setup

The response should look like:

```json
{
  "success": true,
  "message": "System admin setup completed successfully. User your-admin@example.com now has system administrator privileges.",
  "super_user_email": "your-admin@example.com",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "role_assigned": "system_admin"
}
```

## What Happens During Setup

1. **Validation**: Checks if `SUPER_USER_EMAIL` is set
2. **User Lookup**: Finds the user in the database
3. **Role Creation**: Defines `system_admin` role with permissions:
   - Service account management (create, read, write, delete)
   - Role management (create, read, write, delete, assign)
4. **Role Assignment**: Assigns the role to the specified user
5. **Policy Storage**: Saves permissions to the database

## System Admin Capabilities

Once setup is complete, the system administrator can:

- ✅ Create and manage service accounts
- ✅ Create and manage roles
- ✅ Assign roles to users
- ✅ Access all domains (`*`)

## Common Issues

| Issue | Solution |
|-------|----------|
| `SUPER_USER_EMAIL` not set | Set the environment variable |
| User not found | Ensure user exists in database |
| Database connection error | Check database connectivity |
| Role assignment fails | Check Casbin configuration |

## Next Steps

After setup, you can:

1. Create additional roles using the authorization endpoints
2. Set up service accounts for API access
3. Configure domain-specific permissions
4. Assign roles to other users

## Full Documentation

For detailed information, see [Setup Documentation](setup.md). 