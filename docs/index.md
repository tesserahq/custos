# Custos Documentation

Welcome to the Custos documentation! Custos is the centralized authorization service that acts as the **Policy Decision Point (PDP)** in the microservice architecture, managing all authorization logic based on roles and permissions across the system.

## What is Custos?

Custos answers one critical question:

> *"Is user X allowed to perform action Y on resource Z?"*

Custos abstracts the internal authorization engine (Casbin) behind a clean, versioned HTTP API, so that all other services can enforce authorization without needing to know how policies are defined or evaluated.

**Custos** (Latin): Guardian, protector, or watchman — reflecting the service's purpose to guard access to sensitive resources and enforce the rules that govern trust in the platform.

## Core Responsibilities

- Centralize authorization decisions for all services
- Enforce **role-based** and **resource-based access control**
- Expose APIs to check permissions, assign and manage roles, and query permissions for UI display
- Serve as the source of truth for all access control logic and data

## Quick Start

New to Custos? Start here:

1. **[Quick Setup Guide](quick_setup.md)** - Get up and running quickly with your first system administrator
2. **[Setup Documentation](setup.md)** - Detailed information about the setup endpoint and initialization process

## Documentation

### Getting Started

- **[Quick Setup Guide](quick_setup.md)** - Fast track setup for the first system administrator
- **[Setup Documentation](setup.md)** - Comprehensive setup endpoint documentation

### Role Management

- **[Role Management Guide](role_management_guide.md)** - Complete guide to managing roles and permissions
- **[Role Management](role_management.md)** - Detailed role management documentation
- **[Configuration Based Roles](configuration_based_roles.md)** - How to configure and manage roles via configuration files
- **[Multi-Domain Role Management](multi_domain_role_management.md)** - Managing roles across multiple domains and tenants

## Key Concepts

### Subjects

Users, identified by their Auth0 `sub` (e.g. `auth0|abc123`).

### Actions

Defined operations, such as `read`, `write`, `delete`, `create`, `manage`.

### Resources

Things users act on, e.g.:

- Projects (`project:{id}`)
- Accounts (`account:{id}`)
- Other domain entities

### Domains

Authorization domains (typically `account_id`) for scoping roles (multi-tenancy).

### Roles

Assigned per domain (e.g. viewer, editor, admin within an account). Roles map to permitted actions.

## Technology Stack

- **Python** / **FastAPI**
- **Casbin** as the policy engine
- **PostgreSQL** (via Casbin adapter) for persistent policy storage
- REST API (JSON over HTTP)

## How It Works

All other services in the platform delegate authorization checks to Custos via an HTTP call:

```text
[Service] → [Custos] → [Casbin] → allow/deny
```

Services are **not coupled** to Casbin or any policy logic — they just send requests to Custos and receive authorization decisions.

## Need Help?

For issues, questions, or contributions, please refer to the main project repository or contact the development team.
