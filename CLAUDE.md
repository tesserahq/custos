# Custos

Centralized authorization service (Policy Decision Point). Answers "can user X do action Y on resource Z?" for all services in the Tessera platform. Backed by Casbin + PostgreSQL.

## Commands

```bash
# Dev server (hot reload, port 8000)
poetry run dev

# Run tests (requires local PostgreSQL — see Testing below)
pytest

# Lint
ruff check .
black --check .

# Migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
alembic downgrade -1
```

## Environment Variables

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/custos` | |
| `ENV` / `ENVIRONMENT` | `development` | Set to `test` for tests (auto-switches DB) |
| `DISABLE_AUTH` | `false` | Skip auth middleware locally |
| `IDENTIES_API_URL` | — | Required for user fetch during membership create |
| `OIDC_DOMAIN` | `test.oidc.com` | OIDC issuer domain |
| `OIDC_API_AUDIENCE` | `https://test-api` | |
| `SUPER_USER_EMAIL` | — | Comma-separated emails bootstrapped as super users |
| `PORT` | `8000` | |

Config loaded from `.env` via pydantic-settings (`app/config.py`).

## Architecture

```
app/
  commands/       # Business logic — one command per operation (Command pattern)
    memberships/
    policy/
    role/
    setup/
    sync/         # Membership ↔ Casbin sync check/fix
  config/         # casbin_model.conf, default_roles.json
  events/         # NATS CloudEvent builders (membership.created / .deleted)
  middleware/     # RBACMiddleware — enforces Casbin on every request
  models/         # SQLAlchemy ORM models
  repositories/   # Data access — one class per entity, no business logic
  routers/        # FastAPI route handlers (thin — delegate to commands)
  schemas/        # Pydantic request/response models
  config.py       # Settings
  db.py           # SQLAlchemy engine + session
  main.py         # App factory: create_app(testing, auth_middleware)
alembic/          # DB migrations
docs/prds/        # Product Requirements Documents
tests/
  conftest.py     # Session-scoped DB setup, transaction rollback, MockAuthMiddleware
  fixtures/       # User / Role / Permission factory fixtures
```

Middleware stack (outermost → innermost): CORS → Auth → UserOnboarding → **RBAC** → (Rollbar in prod).

## Adding a New Route — RBAC Gotcha

`RBACMiddleware` automatically extracts the resource name from the URL path by taking the last non-ID segment and singularizing it:

- `POST /roles` → resource `custos.role`, action `create`
- `DELETE /memberships/{id}` → resource `custos.membership`, action `delete`
- `POST /sync/check` → resource `custos.check`, action `create`

**When you add a new route, you must add the corresponding permission to `app/config/default_roles.json`** for any role that should have access. The custos-admin role covers all Custos management operations. Run `POST /system/setup` to re-seed roles after changing this file.

Paths in `SKIP_RBAC_PATHS` (in `main.py`) bypass Casbin entirely.

## Memberships Are a Cache

The `memberships` table is explicitly documented as a cache, not the source of truth. The authoritative state lives in Casbin (`casbin_rule` table). When they drift, use:

- `POST /sync/check` — returns orphan Casbin bindings and missing ones for a user
- `POST /sync/fix` — reconciles Casbin to match the DB (DB is source of truth)

Both endpoints require the `custos-admin` role.

## Testing

Tests require a **real local PostgreSQL** instance. `conftest.py` creates `custos_test`, runs Alembic migrations, then drops it at the end of the session. Each test runs in a transaction that is rolled back — no permanent writes.

```bash
# Make sure postgres is running locally, then:
pytest

# Run a specific test file
pytest tests/path/to/test_file.py -v
```

Test client pattern:
```python
# Use the `client` fixture (wraps create_app(testing=True) with MockAuthenticationMiddleware)
def test_something(client, db):
    response = client.post("/roles", json={...})
    assert response.status_code == 201
```

`MockAuthenticationMiddleware` injects `app.state.test_user` into `request.state.user`, bypassing JWT verification. Set the test user via `app.state.test_user = <User ORM instance>`.

## Key Patterns

- **Commands** take repositories as dependencies and orchestrate DB + Casbin + NATS. Routers instantiate commands; commands never import routers.
- **Repositories** never contain business logic — only DB queries. Access DB only through repositories, never via the raw `db` session in commands.
- **Casbin** is a singleton: `get_casbin_repository()` is `@lru_cache()`'d. The default domain for global permissions is `"*"`.
- **Events** are published via NATS using `NatsEventPublisher.publish_sync()`. Event builders live in `app/events/`.
