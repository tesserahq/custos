# Service Accounts

Service accounts are used for API access and automation purposes, separate from regular user accounts. They integrate seamlessly with the existing Casbin RBAC system.

## Overview

Service accounts provide:
- **API Key Authentication**: Secure API access using generated API keys
- **RBAC Integration**: Full integration with Casbin role-based access control
- **Audit Trail**: Tracking of creation, usage, and expiration
- **Multi-tenancy Support**: Domain-based permissions through Casbin

## Key Features

### API Key Management
- Automatic generation of secure API keys (format: `sk_<random_token>`)
- Secure storage using SHA-256 hashing
- Key regeneration capability
- Usage tracking with `last_used_at` timestamp

### RBAC Integration
Service accounts use the same Casbin RBAC system as regular users:
- Service account IDs are used as subjects in Casbin policies
- Support for domain-based permissions
- Role assignment and removal
- Permission checking

### Lifecycle Management
- Active/inactive status
- Optional expiration dates
- Audit trail (created_by, created_at, updated_at)

## Usage Examples

### Creating a Service Account

```python
from app.services.service_account_service import ServiceAccountService
from app.schemas.service_account import ServiceAccountCreate

# Create service account
service_account_data = ServiceAccountCreate(
    name="CI/CD Pipeline",
    description="Service account for automated deployments",
    is_active=True,
    expires_at=datetime.now() + timedelta(days=365)
)

service_account_service = ServiceAccountService(db)
service_account = service_account_service.create_service_account(
    service_account_data, 
    created_by=user_id
)

# The API key is returned only during creation
print(f"API Key: {service_account.api_key}")
```

### Assigning Roles

```python
# Assign admin role to service account
service_account_service.assign_role(
    service_account_id=service_account.id,
    role="admin",
    domain="production"
)

# Assign viewer role for read-only access
service_account_service.assign_role(
    service_account_id=service_account.id,
    role="viewer",
    domain="staging"
)
```

### Checking Permissions

```python
# Check if service account can read users
can_read_users = service_account_service.authorize(
    service_account_id=service_account.id,
    action="read",
    resource="users",
    domain="production"
)

# Check if service account can create projects
can_create_projects = service_account_service.authorize(
    service_account_id=service_account.id,
    action="create",
    resource="projects",
    domain="production"
)
```

### Getting Roles and Permissions

```python
# Get all roles for a service account
roles = service_account_service.get_roles(
    service_account_id=service_account.id,
    domain="production"
)

# Get all permissions for a service account
permissions = service_account_service.get_permissions(
    service_account_id=service_account.id,
    domain="production"
)
```

## API Authentication

Service accounts authenticate using API keys in the Authorization header:

```
Authorization: Bearer sk_your_api_key_here
```

## Casbin Policy Examples

Service accounts can be assigned the same roles as regular users:

```csv
# Assign admin role to service account
g, service-account-uuid, admin, production

# Assign viewer role to service account
g, service-account-uuid, viewer, staging

# Direct permission assignment
p, service-account-uuid, production, users, read
p, service-account-uuid, production, projects, create
```

## Security Best Practices

1. **API Key Security**:
   - Store API keys securely in environment variables
   - Never log or expose API keys
   - Use HTTPS for all API communications
   - Rotate keys regularly

2. **Role Assignment**:
   - Follow the principle of least privilege
   - Use specific roles rather than admin for most use cases
   - Review and audit role assignments regularly

3. **Lifecycle Management**:
   - Set appropriate expiration dates
   - Deactivate unused service accounts
   - Monitor usage patterns
   - Regular security reviews

4. **Monitoring**:
   - Track API usage with `last_used_at`
   - Monitor for unusual access patterns
   - Set up alerts for expired accounts

## Integration with Existing Systems

Service accounts work seamlessly with your existing Casbin setup:

- **Same Policy Format**: Uses existing role definitions and policies
- **Domain Support**: Full multi-tenant support through Casbin domains
- **Audit Integration**: Integrates with existing audit and logging systems
- **Permission Inheritance**: Inherits all Casbin features (hierarchical roles, etc.)

## Migration from User-Based Authentication

If you're migrating from user-based API authentication:

1. Create service accounts for existing API users
2. Assign appropriate roles using existing Casbin policies
3. Update API clients to use service account keys
4. Deactivate or remove old user-based API access
5. Monitor and validate access patterns 