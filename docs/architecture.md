# Custos Architecture

## Overview

Custos is a centralized authorization service built on FastAPI that acts as the Policy Decision Point (PDP) for the platform. It uses a dual-storage architecture where PostgreSQL serves as the source of truth for role and permission management, while Casbin maintains a shadow copy optimized for fast authorization decisions.

## Technology Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migrations**: Alembic
- **Authentication**: OIDC (OpenID Connect) with JWT tokens
- **Dependency Management**: Poetry
- **Observability**: OpenTelemetry, Prometheus metrics, Rollbar error tracking

## Core Architecture Pattern: Shadow Copy

Custos implements a **shadow copy pattern** between PostgreSQL and Casbin:

- **PostgreSQL** (source of truth): Stores roles, permissions, and memberships in normalized relational tables. This is where all management operations (create, update, delete) occur.
- **Casbin** (shadow copy): Maintains an optimized copy of policies and role assignments for fast authorization evaluation. Changes to PostgreSQL are synchronized to Casbin to keep it in sync.

This architecture provides:

- **Ease of management**: PostgreSQL tables are easier to query, audit, and manage
- **Fast authorization**: Casbin is optimized for high-performance policy evaluation
- **Reliability**: PostgreSQL is the source of truth; Casbin can be rebuilt from PostgreSQL if needed

## Data Models

### PostgreSQL Tables (Source of Truth)

#### Roles Table

Stores role definitions with metadata:

- `id` (UUID): Primary key
- `name`: Human-readable role name
- `identifier`: Unique identifier used in Casbin
- `description`: Role description
- Timestamps and soft-delete support

#### Permissions Table

Stores permissions linked to roles:

- `id` (UUID): Primary key
- `role_id` (UUID): Foreign key to roles table
- `object`: Resource type (e.g., `custos.role`, `identies.service_account`)
- `action`: Action type (e.g., `read`, `write`, `create`, `delete`)
- Timestamps and soft-delete support

#### Memberships Table (Shadow Copy)

Maintains a cache of user-role assignments:

- `id` (UUID): Primary key
- `user_id` (UUID): Foreign key to users table
- `role_id` (UUID): Foreign key to roles table
- `domain`: Multi-tenant domain scope (e.g., account ID, `*` for global)
- `domain_metadata` (JSONB): Optional metadata for the domain
- Timestamps and soft-delete support

**Note**: Memberships are a shadow copy. The actual source of truth for role assignments is Casbin, but we maintain this table for easier querying and auditing.

#### Users Table (Shadow Copy)

Maintains a cache of user information from the Identies service:

- `id` (UUID): Primary key
- `email`, `username`, `external_id`: User identifiers
- `first_name`, `last_name`, `avatar_url`: User profile data
- `service_account`: Boolean flag
- Timestamps and soft-delete support

**Note**: Users are cached from the Identies service and may have inconsistent data. Identies is the source of truth for user information.

### Casbin Storage (Shadow Copy)

Casbin uses the same PostgreSQL database but stores data in its own optimized format:

#### Policies (p)

Represents role permissions synced from the `permissions` table:

```text
p, <role_identifier>, <domain>, <object>, <action>
```

Example: `p, custos-admin, *, custos.role, read`

#### Role Assignments (g)

Represents user-role assignments synced from the `memberships` table:

```text
g, <user_id>, <role_identifier>, <domain>
```

Example: `g, user-123, custos-admin, *`

## Data Flow and Synchronization

### Role and Permission Management Flow

```text
┌─────────────────┐
│  API Request    │
│  (Create Role)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  PostgreSQL             │
│  - roles table          │
│  - permissions table    │
│  (Source of Truth)      │
└────────┬────────────────┘
         │
         │ Sync via
         │ SyncRolePolicyCommand
         ▼
┌─────────────────────────┐
│  Casbin                 │
│  - Policies (p)         │
│  (Shadow Copy)          │
└─────────────────────────┘
```

1. **Create/Update Role**: Changes are written to PostgreSQL `roles` and `permissions` tables
2. **Sync to Casbin**: `SyncRolePolicyCommand` reads permissions from PostgreSQL and creates corresponding Casbin policies
3. **Policy Format**: Each permission becomes a policy: `p, <role_identifier>, <domain>, <object>, <action>`

### Membership (Role Assignment) Flow

```text
┌─────────────────┐
│  API Request    │
│  (Assign Role)  │
└────────┬────────┘
         │
         │
         ├──────────────────────┐
         │                      │
         ▼                      ▼
┌─────────────────────────┐  ┌─────────────────────────┐
│  PostgreSQL             │  │  Casbin                 │
│  - memberships table    │  │  - Role Assignments (g) │
│  (Shadow Copy)          │  │  (Source of Truth)      │
└─────────────────────────┘  └─────────────────────────┘
```

1. **Assign Role**: `CreateBindingCommand` simultaneously:
   - Creates a record in PostgreSQL `memberships` table (for querying/auditing)
   - Assigns the role in Casbin via `casbin_service.assign_role()` (for authorization)

2. **Authorization Check**: When evaluating permissions, Casbin:
   - Looks up user's roles (g rules)
   - Uses those roles to find matching policies (p rules)
   - Returns allow/deny decision

### Authorization Request Flow

```text
┌─────────────────┐
│  Service        │
│  (e.g., Vaulta) │
└────────┬────────┘
         │
         │ POST /authorization/authorize
         │ { user_id, action, resource, domain }
         ▼
┌─────────────────────────┐
│  CasbinService          │
│  authorize()            │
└────────┬────────────────┘
         │
         │ enforcer.enforce()
         ▼
┌─────────────────────────┐
│  Casbin                 │
│  - Check role (g)       │
│  - Check policy (p)     │
│  - Return allow/deny    │
└────────┬────────────────┘
         │
         │ { allowed: true/false }
         ▼
┌─────────────────┐
│  Service        │
│  (Response)     │
└─────────────────┘
```

**Important**: Authorization checks only query Casbin, never PostgreSQL. This ensures fast response times even under high load.

## Key Components

### Services

- **RoleService**: Manages roles and permissions in PostgreSQL
- **PermissionService**: Manages permissions linked to roles
- **MembershipService**: Manages membership records (shadow copy)
- **UserService**: Manages user cache from Identies
- **CasbinService**: Wrapper around Casbin enforcer for authorization checks and policy management

### Commands

- **CreateRolesBatchCommand**: Creates roles and permissions in PostgreSQL, then syncs policies to Casbin
- **SyncRolePolicyCommand**: Syncs role permissions from PostgreSQL to Casbin policies
- **CreateBindingCommand**: Assigns roles to users in both PostgreSQL (memberships) and Casbin
- **SetupCommand**: Initializes system by importing roles from JSON and assigning to super users

### Routers

- **authorization**: `/authorization/authorize` - Authorization checks
- **role**: Role CRUD operations and policy binding
- **permission**: Permission management
- **membership**: Membership queries (read-only, for UI/auditing)
- **system**: `/system/setup` - System initialization

## Multi-Tenancy Support

Custos supports multi-tenancy through **domains**:

- **Global Domain** (`*`): Roles assigned in the global domain have access across all tenants
- **Tenant-Specific Domains**: Roles can be scoped to specific accounts/organizations
- **Domain in Policies**: Each policy includes a domain parameter: `p, <role>, <domain>, <object>, <action>`
- **Domain in Assignments**: Each role assignment includes a domain: `g, <user>, <role>, <domain>`

The Casbin model uses domain-aware matching to ensure users only have access to resources in domains where they have assigned roles.

## Event-Driven Architecture

Custos publishes events when data changes:

- **Role Events**: `role.created`, `role.updated`, `role.deleted`
- **Permission Events**: `permission.created`, `permission.updated`, `permission.deleted`
- **Binding Events**: `bind.created`, `bind.deleted`

These events allow other services to react to authorization changes in real-time.

## Consistency Guarantees

### Eventual Consistency

PostgreSQL and Casbin are **eventually consistent**:

- Changes to PostgreSQL are immediately committed
- Synchronization to Casbin happens within the same request/transaction when possible
- If Casbin sync fails, the PostgreSQL change still succeeds (you can re-sync later)

### Recovery Strategy

If Casbin data becomes inconsistent:

1. **Rebuild Policies**: Use `SyncRolePolicyCommand` to rebuild policies for specific roles
2. **Rebuild Assignments**: Re-create memberships from PostgreSQL `memberships` table
3. **Full Rebuild**: Clear Casbin and re-run setup or manually sync all roles and memberships

## Performance Considerations

- **Authorization Checks**: Query only Casbin (fast, optimized)
- **Management Operations**: Write to PostgreSQL first, then sync to Casbin
- **Read Queries**: Use PostgreSQL for complex queries, role listings, user permissions for UI
- **Caching**: Casbin enforcer loads policies into memory for fast evaluation

## Security Considerations

- **JWT Authentication**: All endpoints require valid JWT tokens from Auth0 (except public endpoints)
- **RBAC Middleware**: Validates user permissions before allowing access to management endpoints
- **Soft Deletes**: All models support soft deletion for audit trails
- **Domain Isolation**: Multi-tenant isolation enforced at the Casbin policy level
