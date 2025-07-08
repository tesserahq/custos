# Multi-Domain Role Management

This document explains how to efficiently manage roles and permissions across multiple domains (tenants) in the Custos authorization system.

## The Problem

In a multi-tenant system with 200 domains, managing role permissions can become challenging:

- **Manual Updates**: Adding a new permission requires updating each domain individually
- **Inconsistency**: Different domains might have different role definitions
- **Maintenance Overhead**: Changes require 200 separate operations
- **Error Prone**: Manual updates can lead to inconsistencies

## Solutions

### 1. Role Templates System (Recommended)

The role templates system provides a centralized way to manage roles across multiple domains.

#### Key Features

- **Single Source of Truth**: Define roles once in a template
- **Bulk Operations**: Apply templates to multiple domains simultaneously
- **Version Control**: Templates can be versioned and tracked
- **Incremental Updates**: Add/remove permissions without recreating entire roles

#### How It Works

1. **Create Templates**: Define role configurations in YAML templates
2. **Apply Templates**: Apply templates to one or multiple domains
3. **Update Templates**: Modify templates and reapply to update all domains
4. **Incremental Changes**: Add/remove specific permissions

#### API Endpoints

```bash
# Create a template
POST /authorization/templates
{
  "template_name": "standard-roles",
  "role_config": {
    "roles": {
      "admin": {
        "permissions": {
          "users": ["read", "write", "delete", "create"],
          "documents": ["read", "write", "delete", "create"]
        }
      }
    }
  }
}

# Apply template to multiple domains
POST /authorization/templates/standard-roles/apply-multiple
{
  "domains": ["tenant-1", "tenant-2", "tenant-3"],
  "overwrite_existing": true
}

# Add permission to template
POST /authorization/templates/standard-roles/add-permission
{
  "role_name": "admin",
  "resource": "reports",
  "action": "export"
}

# Update template and apply to all domains
POST /authorization/templates/standard-roles/update-and-apply
{
  "updated_config": { /* updated role config */ },
  "domains": ["tenant-1", "tenant-2", "tenant-3"],
  "overwrite_existing": true
}
```

#### Workflow Example

```python
# 1. Create a standard template
template_config = {
    "roles": {
        "admin": {
            "permissions": {
                "users": ["read", "write", "delete", "create"],
                "documents": ["read", "write", "delete", "create"]
            }
        }
    }
}

# 2. Apply to all 200 domains
domains = [f"tenant-{i}" for i in range(1, 201)]
apply_template_to_domains("standard-roles", domains)

# 3. Add new permission to all domains
add_permission_to_template("standard-roles", "admin", "reports", "export")
update_template_and_apply("standard-roles", updated_config, domains)
```

### 2. Bulk Operations API

For one-time operations, you can use bulk endpoints:

```bash
# Bulk role setup
POST /authorization/setup-roles-bulk
{
  "domains": ["tenant-1", "tenant-2", "tenant-3"],
  "type": "yaml",
  "content": "roles:\n  admin:\n    permissions:\n      users: [read, write]"
}
```

### 3. Database-Level Operations

For advanced scenarios, you can perform database-level operations:

```sql
-- Add permission to all domains
INSERT INTO casbin_rule (ptype, v0, v1, v2, v3)
SELECT 'p', 'admin', 'reports', 'export', domain
FROM (SELECT DISTINCT v3 as domain FROM casbin_rule WHERE v3 LIKE 'tenant-%') as domains;
```

## Best Practices

### 1. Template Organization

```
config/templates/
├── standard-roles.yaml      # Basic roles for most tenants
├── enterprise-roles.yaml    # Extended roles for enterprise tenants
├── custom-roles.yaml        # Custom roles for specific use cases
└── legacy-roles.yaml        # Legacy role definitions
```

### 2. Naming Conventions

- **Template Names**: Use descriptive names like `standard-roles`, `enterprise-roles`
- **Domain Names**: Use consistent naming like `tenant-{id}` or `org-{name}`
- **Role Names**: Use standard names like `admin`, `editor`, `viewer`

### 3. Version Control

- Store templates in version control
- Use semantic versioning for templates
- Document changes in template versions

### 4. Testing

- Test templates on a subset of domains first
- Use staging environments for template validation
- Implement rollback procedures

## Migration Strategies

### From Manual to Templates

1. **Audit Current State**: Document existing roles in each domain
2. **Create Templates**: Convert existing roles to templates
3. **Apply Templates**: Apply templates to all domains
4. **Verify Consistency**: Ensure all domains have consistent roles
5. **Update Processes**: Use templates for future changes

### Incremental Migration

1. **Start with New Domains**: Apply templates to new domains only
2. **Gradual Migration**: Migrate existing domains in batches
3. **Validation**: Verify roles after each batch
4. **Complete Migration**: Apply templates to all remaining domains

## Monitoring and Maintenance

### 1. Template Validation

```python
# Validate template before applying
def validate_template(template_config):
    required_fields = ['roles']
    for field in required_fields:
        if field not in template_config:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate role structure
    for role_name, role_config in template_config['roles'].items():
        if 'permissions' not in role_config:
            raise ValueError(f"Role {role_name} missing permissions")
```

### 2. Consistency Checks

```python
# Check if all domains have consistent roles
def check_domain_consistency(template_name, domains):
    template = get_template(template_name)
    inconsistencies = []
    
    for domain in domains:
        domain_roles = get_domain_roles(domain)
        if not roles_match(template['roles'], domain_roles):
            inconsistencies.append(domain)
    
    return inconsistencies
```

### 3. Automated Updates

```python
# Automated template updates
def auto_update_template(template_name, new_permissions):
    template = get_template(template_name)
    
    for role_name, permissions in new_permissions.items():
        add_permissions_to_role(template, role_name, permissions)
    
    # Apply to all domains
    domains = get_all_domains()
    update_template_and_apply(template_name, template, domains)
```

## Performance Considerations

### 1. Batch Operations

- Use bulk endpoints for multiple domains
- Process domains in batches of 50-100
- Implement retry logic for failed operations

### 2. Caching

- Cache template configurations
- Cache domain role mappings
- Use Redis for template caching

### 3. Database Optimization

- Use database transactions for bulk operations
- Index domain columns for faster queries
- Consider read replicas for large deployments

## Troubleshooting

### Common Issues

1. **Template Not Found**: Ensure template exists before applying
2. **Permission Conflicts**: Check for existing permissions before adding
3. **Domain Isolation**: Verify domains are properly isolated
4. **Performance Issues**: Use batch operations for large numbers of domains

### Debugging Commands

```bash
# List all templates
GET /authorization/templates

# Get specific template
GET /authorization/templates/standard-roles

# Check domain roles
GET /authorization/domains/{domain}/roles

# Validate template
POST /authorization/templates/validate
```

## Conclusion

The role templates system provides an efficient way to manage roles across multiple domains. By using templates, you can:

- **Reduce Maintenance**: Single template definition for all domains
- **Ensure Consistency**: All domains have identical role structures
- **Simplify Updates**: Change once, apply everywhere
- **Scale Efficiently**: Handle hundreds of domains with minimal effort

For most use cases, the template system is the recommended approach. For one-time operations or migrations, consider bulk operations or database-level changes. 