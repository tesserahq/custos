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

## Getting Started

- **[Quick Setup Guide](quick_setup.md)** - Fast track setup for the first system administrator
- **[Architecture](architecture.md)** - Learn about the system design, core data models, and how Custos integrates PostgreSQL and Casbin.
