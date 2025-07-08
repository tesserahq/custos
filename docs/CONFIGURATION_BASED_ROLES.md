# Configuration-Based Role Definition

This document explains how to use configuration files (YAML or CSV) to define roles and permissions in Custos instead of hardcoding them in Python.

## Overview

Casbin supports multiple formats for defining policies and roles. Instead of hardcoding role definitions in Python, you can now use:

1. **YAML files** - Human-readable, hierarchical format
2. **CSV files** - Simple, tabular format
3. **Database** - Your current PostgreSQL approach

## Benefits of Configuration Files

- **Maintainability**: Easy to modify roles without code changes
- **Version Control**: Track role changes in Git
- **Environment-Specific**: Different configs for dev/staging/prod
- **Non-Technical Users**: Business users can modify roles
- **Validation**: Built-in configuration validation
- **Flexibility**: Support for multiple formats

## Configuration Formats

### 1. YAML Format (`roles.yaml`)

The YAML format is the most readable and recommended approach:

```yaml
# Role definitions for Custos authorization system
roles:
  admin:
    description: "Full system access within the domain"
    permissions:
      users:
        - read
        - write
        - delete
        - create
      projects:
        - read
        - write
        - delete
        - create
      documents:
        - read
        - write
        - delete
        - create
      roles:
        - read
        - write
        - delete
        - create
      settings:
        - read
        - write

  editor:
    description: "Content creation and editing permissions"
    permissions:
      users:
        - read
      projects:
        - read
        - write
        - create
      documents:
        - read
        - write
        - create
      settings:
        - read

  viewer:
    description: "Read-only access to all resources"
    permissions:
      users:
        - read
      projects:
        - read
      documents:
        - read
      settings:
        - read

  moderator:
    description: "Content moderation with limited user management"
    permissions:
      users:
        - read
        - write
      comments:
        - read
        - write
        - delete
      documents:
        - read
        - write
```

### 2. CSV Format (`roles.csv`)

The CSV format follows Casbin's native policy format:

```csv
# Casbin Policy CSV Format
# Format: p, role, domain, resource, action
p, admin, *, users, read
p, admin, *, users, write
p, admin, *, users, delete
p, admin, *, users, create
p, admin, *, projects, read
p, admin, *, projects, write
p, admin, *, projects, delete
p, admin, *, projects, create
p, admin, *, documents, read
p, admin, *, documents, write
p, admin, *, documents, delete
p, admin, *, documents, create
p, admin, *, roles, read
p, admin, *, roles, write
p, admin, *, roles, delete
p, admin, *, roles, create
p, admin, *, settings, read
p, admin, *, settings, write

p, editor, *, users, read
p, editor, *, projects, read
p, editor, *, projects, write
p, editor, *, projects, create
p, editor, *, documents, read
p, editor, *, documents, write
p, editor, *, documents, create
p, editor, *, settings, read

p, viewer, *, users, read
p, viewer, *, projects, read
p, viewer, *, documents, read
p, viewer, *, settings, read

p, moderator, *, users, read
p, moderator, *, users, write
p, moderator, *, comments, read
p, moderator, *, comments, write
p, moderator, *, comments, delete
p, moderator, *, documents, read
p, moderator, *, documents, write
```

## API Endpoints

### Set Up Roles from Configuration

```http
POST /authorization/setup-roles-from-config/{domain}?config_file=roles.yaml
```

**Example:**
```bash
# Set up roles from YAML config
curl -X POST "http://localhost:8000/authorization/setup-roles-from-config/account-123?config_file=roles.yaml" \
  -H "Authorization: Bearer your-token"

# Set up roles from CSV config
curl -X POST "http://localhost:8000/authorization/setup-roles-from-config/account-123?config_file=roles.csv" \
  -H "Authorization: Bearer your-token"
```

**Response:**
```json
{
  "domain": "account-123",
  "config_file": "roles.yaml",
  "results": {
    "admin": true,
    "editor": true,
    "viewer": true,
    "moderator": true
  },
  "success_count": 4,
  "total_roles": 4,
  "message": "Roles setup from config completed: 4/4 roles created successfully"
}
```

### Get Available Roles

```http
GET /authorization/available-roles?config_file=roles.yaml
```

**Example:**
```bash
curl -X GET "http://localhost:8000/authorization/available-roles?config_file=roles.yaml" \
  -H "Authorization: Bearer your-token"
```

**Response:**
```json
{
  "config_file": "roles.yaml",
  "available_roles": ["admin", "editor", "viewer", "moderator"],
  "count": 4
}
```

### Validate Configuration

```http
GET /authorization/validate-config?config_file=roles.yaml
```

**Example:**
```bash
curl -X GET "http://localhost:8000/authorization/validate-config?config_file=roles.yaml" \
  -H "Authorization: Bearer your-token"
```

**Response:**
```json
{
  "config_file": "roles.yaml",
  "valid": true,
  "errors": [],
  "warnings": []
}
```

## Python Usage

### Using the RoleConfigService

```python
from app.services.role_config_service import role_config_service

# Set up roles from YAML configuration
domain = "account-123"
results = role_config_service.define_roles_from_yaml(domain, "roles.yaml")

# Set up roles from CSV configuration
results = role_config_service.define_roles_from_csv(domain, "roles.csv")

# Get available roles
roles = role_config_service.get_available_roles("roles.yaml")

# Validate configuration
validation = role_config_service.validate_configuration("roles.yaml")
if validation["valid"]:
    print("Configuration is valid!")
else:
    print(f"Configuration errors: {validation['errors']}")
```

### Loading Configuration

```python
# Load YAML configuration
config = role_config_service.load_roles_from_yaml("roles.yaml")
admin_permissions = config["roles"]["admin"]["permissions"]

# Load CSV configuration
policies = role_config_service.load_roles_from_csv("roles.csv")
for policy in policies:
    role, resource, action = policy[1], policy[3], policy[4]
    print(f"Role {role} can {action} on {resource}")
```

## Migration from Hardcoded Roles

### Before (Hardcoded)

```python
# Old approach - hardcoded in Python
def define_admin_role(self, domain: str) -> bool:
    admin_permissions = [
        ("admin", domain, "users", "read"),
        ("admin", domain, "users", "write"),
        ("admin", domain, "users", "delete"),
        ("admin", domain, "users", "create"),
        # ... many more hardcoded permissions
    ]
    
    for subject, dom, obj, action in admin_permissions:
        casbin_service.add_policy(subject, obj, action, domain=dom)
```

### After (Configuration-Based)

```python
# New approach - load from configuration
def setup_roles_from_config(self, domain: str) -> Dict[str, bool]:
    return role_config_service.define_roles_from_yaml(domain, "roles.yaml")
```

## Best Practices

### 1. Use YAML for Complex Configurations

YAML is recommended for most use cases because it's:
- Human-readable
- Supports comments
- Hierarchical structure
- Easy to validate

### 2. Use CSV for Simple Configurations

CSV is good for:
- Simple role definitions
- Bulk policy imports
- Integration with external tools

### 3. Environment-Specific Configurations

Create different configuration files for different environments:

```
app/config/
├── roles.yaml              # Default roles
├── roles-dev.yaml          # Development roles
├── roles-staging.yaml      # Staging roles
└── roles-prod.yaml         # Production roles
```

### 4. Version Control

Track configuration changes in Git:

```bash
git add app/config/roles.yaml
git commit -m "Add moderator role with comment management permissions"
```

### 5. Validation

Always validate configurations before deployment:

```python
# Validate before using
validation = role_config_service.validate_configuration("roles.yaml")
if not validation["valid"]:
    raise ValueError(f"Invalid configuration: {validation['errors']}")
```

## Comparison with Hardcoded Approach

| Aspect | Hardcoded | Configuration Files |
|--------|-----------|-------------------|
| **Maintainability** | Requires code changes | File edits only |
| **Version Control** | Code commits | Dedicated config tracking |
| **Non-Technical Users** | No | Yes |
| **Environment-Specific** | Conditional logic | Different files |
| **Validation** | Runtime only | Pre-deployment |
| **Performance** | Slightly faster | Negligible difference |
| **Flexibility** | Limited | High |

## Testing

The configuration-based approach includes comprehensive testing:

```python
# Test loading configurations
def test_load_roles_from_yaml():
    config = role_config_service.load_roles_from_yaml("roles.yaml")
    assert "admin" in config["roles"]

# Test role definition
def test_define_roles_from_config():
    results = role_config_service.define_roles_from_yaml("test-domain", "roles.yaml")
    assert results["admin"] is True

# Test validation
def test_validate_configuration():
    validation = role_config_service.validate_configuration("roles.yaml")
    assert validation["valid"] is True
```

## Troubleshooting

### Common Issues

1. **File Not Found**
   ```
   FileNotFoundError: Configuration file not found: app/config/roles.yaml
   ```
   **Solution**: Ensure the configuration file exists in `app/config/`

2. **Invalid YAML Syntax**
   ```
   yaml.YAMLError: mapping values are not allowed here
   ```
   **Solution**: Check YAML syntax and indentation

3. **Invalid CSV Format**
   ```
   IndexError: list index out of range
   ```
   **Solution**: Ensure CSV has 5 columns: `p, role, domain, resource, action`

4. **Permission Denied**
   ```
   PermissionError: [Errno 13] Permission denied
   ```
   **Solution**: Check file permissions on configuration files

### Debugging

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger('app.services.role_config_service').setLevel(logging.DEBUG)
```

## Conclusion

Configuration-based role definition provides a more maintainable and flexible approach to managing roles and permissions in Custos. It separates configuration from code, making it easier to manage and modify authorization policies without requiring code changes.

The YAML format is recommended for most use cases due to its readability and structure, while CSV format is suitable for simple configurations or bulk imports. 