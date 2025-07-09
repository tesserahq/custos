# Setup Endpoint Documentation

## Overview

The setup endpoint (`/setup`) is a critical initialization endpoint that establishes the first system administrator in the Custos authorization system. This endpoint is designed to be called once during the initial deployment or when setting up a new environment.

## Purpose

The setup endpoint serves several important functions:

1. **System Administrator Creation**: Establishes the first system administrator with global privileges
2. **Role Definition**: Creates the `system_admin` role with appropriate permissions
3. **User Assignment**: Assigns the system admin role to a designated user
4. **System Initialization**: Ensures the authorization system is properly configured

## Prerequisites

Before calling the setup endpoint, ensure the following:

1. **Database Connection**: The application must be able to connect to the PostgreSQL database
2. **User Existence**: A user must exist in the database with the email specified in the `SUPER_USER_EMAIL` environment variable
3. **Environment Variable**: The `SUPER_USER_EMAIL` environment variable must be set

## Environment Configuration

Set the following environment variable:

```bash
export SUPER_USER_EMAIL="admin@yourdomain.com"
```

Or add it to your `.env` file:

```env
SUPER_USER_EMAIL=admin@yourdomain.com
```

## API Endpoint

### POST `/setup`

**Description**: Initializes the system administrator role and assigns it to the specified user.

**Request**:
```http
POST /setup
Content-Type: application/json
```

**Response**:
```json
{
  "success": true,
  "message": "System admin setup completed successfully. User admin@yourdomain.com now has system administrator privileges.",
  "super_user_email": "admin@yourdomain.com",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "role_assigned": "system_admin"
}
```

## Process Flow

When the setup endpoint is called, the following sequence occurs:

### 1. Environment Validation
- Checks if `SUPER_USER_EMAIL` environment variable is set
- Returns HTTP 400 if the variable is missing

### 2. User Verification
- Looks up the user in the database using the provided email
- Returns HTTP 404 if no user is found with that email

### 3. Role Definition
The system admin role is defined with the following permissions:

| Resource | Actions |
|----------|---------|
| `service_accounts` | `create`, `read`, `write`, `delete` |
| `roles` | `create`, `read`, `write`, `delete`, `assign` |

These permissions are added to the Casbin policy store with domain `*` (global access).

### 4. Role Assignment
- Assigns the `system_admin` role to the specified user
- Uses domain `*` for global access across all domains
- Saves the policy to the database

### 5. Success Response
Returns a success response with details about the setup operation.

## Error Handling

The setup endpoint handles various error scenarios:

### Missing Environment Variable
```json
{
  "detail": "SUPER_USER_EMAIL environment variable is not set. Cannot proceed with system admin setup."
}
```

### User Not Found
```json
{
  "detail": "No user found with email: nonexistent@example.com. Please ensure the user exists in the database before running setup."
}
```

### Role Definition Failure
```json
{
  "detail": "Failed to define system admin role. Check logs for details."
}
```

### Role Assignment Failure
```json
{
  "detail": "Failed to assign system admin role to user. Check logs for details."
}
```

### Unexpected Errors
```json
{
  "detail": "Unexpected error during system admin setup: [error details]"
}
```

## System Admin Permissions

Once setup is complete, the system administrator has the following capabilities:

### Service Account Management
- Create new service accounts
- Read service account details
- Update service account information
- Delete service accounts

### Role Management
- Create new roles
- Read role definitions and permissions
- Update role permissions
- Delete roles
- Assign roles to users

## Security Considerations

1. **One-Time Use**: The setup endpoint should only be called once during initial deployment
2. **Environment Variable**: The `SUPER_USER_EMAIL` should be set securely and not committed to version control
3. **User Verification**: Ensure the specified user exists and is legitimate before running setup
4. **Network Security**: The setup endpoint should be protected in production environments

## Usage Examples

### Using curl
```bash
# Set the environment variable
export SUPER_USER_EMAIL="admin@yourdomain.com"

# Call the setup endpoint
curl -X POST http://localhost:8000/setup \
  -H "Content-Type: application/json"
```

### Using Python requests
```python
import requests
import os

# Set environment variable
os.environ["SUPER_USER_EMAIL"] = "admin@yourdomain.com"

# Call setup endpoint
response = requests.post("http://localhost:8000/setup")
print(response.json())
```

### Using the application directly
```python
from app.routers.setup import setup_super_user
from app.db import get_db

# Get database session
db = next(get_db())

# Call setup function
result = setup_super_user(db)
print(result)
```

## Testing

The setup endpoint includes comprehensive test coverage in `tests/app/routers/test_setup.py`. Tests cover:

- Successful setup scenarios
- Missing environment variable handling
- User not found scenarios
- Role definition failures
- Role assignment failures
- Unexpected error handling
- Real Casbin integration testing

To run the tests:

```bash
poetry run pytest tests/app/routers/test_setup.py -v
```

## Monitoring and Logging

The setup process includes detailed logging at each step:

- Environment variable validation
- User lookup operations
- Role definition progress
- Role assignment status
- Final setup completion

Check application logs to monitor the setup process and troubleshoot any issues.

## Troubleshooting

### Common Issues

1. **User Not Found**: Ensure the user exists in the database before running setup
2. **Database Connection**: Verify database connectivity and credentials
3. **Environment Variable**: Check that `SUPER_USER_EMAIL` is properly set
4. **Casbin Configuration**: Ensure Casbin model and adapter are properly configured

### Debug Steps

1. Check application logs for detailed error messages
2. Verify database connection and user existence
3. Confirm environment variable is set correctly
4. Test Casbin service initialization
5. Verify database permissions for policy storage

## Related Documentation

- [Role Management Guide](ROLE_MANAGEMENT_GUIDE.md)
- [Service Accounts](SERVICE_ACCOUNTS.md)
- [Multi-Domain Role Management](MULTI_DOMAIN_ROLE_MANAGEMENT.md)
- [Configuration Based Roles](CONFIGURATION_BASED_ROLES.md) 