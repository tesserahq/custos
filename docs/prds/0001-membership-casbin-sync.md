## Problem Statement

Users who have been removed from a role still retain access to protected resources. When a membership is deleted via the API, the Casbin role binding (g rule) that grants access is not reliably removed, leaving a stale authorization entry in Casbin. This is an authorization bug with a security impact: revoked access is not enforced immediately.

The underlying cause is a domain mismatch during deletion. Memberships are created with a domain (defaulting to `"*"`), which causes Casbin to store the binding scoped to that domain. However, the delete endpoint passes `domain=None` to the removal command, causing Casbin to call the wrong removal method (`delete_role_for_user` instead of `delete_roles_for_user_in_domain`). The binding in the `"*"` domain is never removed.

Beyond the immediate bug, there is no way to inspect or repair the state of Casbin role bindings relative to the database memberships. When drift occurs — due to this bug, manual Casbin edits, failed transactions, or migrations — there is no tooling to detect or correct it.

## Solution

The solution has two parts:

1. **Bug fix**: Correct the `DELETE /memberships/{id}` endpoint to pass the membership's actual domain to the delete command, ensuring the Casbin binding is removed with the correct domain context.

2. **Sync tooling**: Add a new `/sync` router with two endpoints that allow administrators to inspect and repair divergence between the database memberships and Casbin g rules (role bindings):
   - `POST /sync/check` — a read-only endpoint that returns all discrepancies for a given user: Casbin bindings with no matching active DB membership, and DB memberships with no matching Casbin binding.
   - `POST /sync/fix` — a write endpoint that reconciles Casbin to match the database (DB is source of truth), both removing orphan Casbin bindings and adding missing ones, publishing NATS events for each change made.

## User Stories

1. As a security administrator, I want role removal to immediately revoke a user's access so that offboarding and role changes are enforced without delay.
2. As a security administrator, I want the DELETE membership endpoint to correctly remove the Casbin binding regardless of what domain the membership was created with.
3. As an operator, I want to call a check endpoint with a user ID so that I can see whether that user's DB memberships are in sync with their Casbin role bindings.
4. As an operator, I want the check endpoint to accept an optional domain parameter so that I can narrow the inspection to a specific tenant when debugging multi-tenant issues.
5. As an operator, I want the check response to clearly separate orphan Casbin bindings (in Casbin, not in DB) from missing Casbin bindings (in DB, not in Casbin) so that I understand the nature of the drift at a glance.
6. As an operator, I want to call a fix endpoint with a user ID so that I can reconcile Casbin to match the database in a single operation.
7. As an operator, I want the fix endpoint to accept an optional domain parameter so that I can scope reconciliation to a specific tenant without touching other domains.
8. As an operator, I want the fix endpoint to remove orphan Casbin role bindings so that stale access grants are eliminated.
9. As an operator, I want the fix endpoint to add missing Casbin role bindings so that users who should have access but don't are restored.
10. As an operator, I want the fix endpoint to publish `membership.deleted` NATS events for each Casbin binding removed so that downstream services stay consistent.
11. As an operator, I want the fix endpoint to publish `membership.created` NATS events for each Casbin binding added so that downstream services can react to restored memberships.
12. As an operator, I want the fix response to list exactly which bindings were removed and which were added so that I have a full audit trail of what was changed.
13. As an administrator, I want both sync endpoints to be restricted to Custos admins so that sensitive authorization state cannot be read or modified by unauthorized callers.
14. As a developer, I want the sync check logic to correctly handle multi-domain users by comparing bindings across all domains (or a filtered domain) so that drift in any domain is detected.
15. As a developer, I want the `SyncCheckCommand` to be a pure read operation with no side effects so that it is safe to call repeatedly for monitoring or debugging without risk.
16. As a developer, I want the fix endpoint to be idempotent so that calling it multiple times on an already-synced user produces no changes and no duplicate events.
17. As a future operator, I want the `/sync` router to be extensible so that additional sync targets (e.g., batch user checks, policy rule sync) can be added without restructuring the API.

## Implementation Decisions

### Bug Fix

- The `DELETE /memberships/{membership_id}` router handler currently passes `domain=None` to `DeleteMembershipCommand`. It must be changed to pass `membership.domain` (the actual domain stored on the membership record) so that `CasbinRepository.remove_role()` uses the domain-aware removal path (`delete_roles_for_user_in_domain`) instead of the global removal path.

### New Modules

**`SyncCheckCommand`**
- Read-only command that accepts `user_id` (string) and optional `domain`.
- Retrieves all active (non-soft-deleted) DB memberships for the user, optionally filtered by domain.
- Retrieves all Casbin g rules for the user. When no domain is specified, it must retrieve bindings across all domains — this requires using `enforcer.get_filtered_grouping_policy(0, user_id)` on the raw Casbin enforcer, since `get_user_roles()` only handles one domain at a time.
- Compares the two sets as `(user_id, role_identifier, domain)` triples.
- Returns a `SyncCheckResult` value object with: `in_sync: bool`, `orphan_casbin_bindings: list`, `missing_casbin_bindings: list`.
- Dependencies: `MembershipRepository`, `RoleRepository`, `CasbinRepository`.

**`SyncFixCommand`**
- Write command that accepts `user_id` (string) and optional `domain`.
- Internally runs `SyncCheckCommand` to determine what needs to change.
- For each orphan Casbin binding: calls `CasbinRepository.remove_role()` with the correct domain, then publishes a `membership.deleted` event.
- For each missing Casbin binding: calls `CasbinRepository.assign_role()` with the correct domain, then publishes a `membership.created` event.
- Returns a `SyncFixResult` value object with: `removed_from_casbin: list`, `added_to_casbin: list`, `events_published: int`.
- Dependencies: `MembershipRepository`, `RoleRepository`, `CasbinRepository`, `NatsEventPublisher`.

**`SyncRouter`**
- New router at prefix `/sync`, tag `Sync`.
- `POST /sync/check`: calls `SyncCheckCommand`, returns `SyncCheckResponse`. Read-only, no DB writes.
- `POST /sync/fix`: calls `SyncFixCommand`, returns `SyncFixResponse`. Mutates Casbin state and publishes events.
- Both endpoints require the caller to be a Custos admin (same authorization pattern as other privileged endpoints).
- Router registered in `app/routers/__init__.py`.

**`SyncSchemas`**
- `SyncCheckRequest`: `user_id: str`, `domain: Optional[str]`.
- `SyncCheckResponse`: `in_sync: bool`, `orphan_casbin_bindings: list[CasbinBinding]`, `missing_casbin_bindings: list[CasbinBinding]`.
- `SyncFixRequest`: `user_id: str`, `domain: Optional[str]`.
- `SyncFixResponse`: `removed_from_casbin: list[CasbinBinding]`, `added_to_casbin: list[CasbinBinding]`, `events_published: int`.
- `CasbinBinding`: `user_id: str`, `role_identifier: str`, `domain: Optional[str]` — a shared value object describing a single role binding triple.

### API Contracts

```
POST /sync/check
Body: { "user_id": "...", "domain": "..." (optional) }
Response 200: {
  "in_sync": false,
  "orphan_casbin_bindings": [{ "user_id": "...", "role_identifier": "...", "domain": "..." }],
  "missing_casbin_bindings": [{ "user_id": "...", "role_identifier": "...", "domain": "..." }]
}

POST /sync/fix
Body: { "user_id": "...", "domain": "..." (optional) }
Response 200: {
  "removed_from_casbin": [...],
  "added_to_casbin": [...],
  "events_published": 3
}
```

### Domain Matching Logic

- A DB membership `(user_id, role_id, domain)` matches a Casbin binding `(user_id, role_identifier, domain)` when all three fields are equal and the role's identifier corresponds to the role_id.
- `NULL` domain in DB must be treated as equivalent to a Casbin binding with no domain (global binding).
- `"*"` domain is a valid, distinct domain value — not the same as `NULL`.

## Testing Decisions

Good tests verify externally observable behavior (return values, state changes, published events) and do not assert on internal implementation details such as which repository method was called.

**`SyncCheckCommand`**
- Given a user with active DB memberships and matching Casbin bindings: `in_sync` is `True`, both lists are empty.
- Given a user with a Casbin binding but no corresponding DB membership: the binding appears in `orphan_casbin_bindings`.
- Given a user with a DB membership but no corresponding Casbin binding: the membership appears in `missing_casbin_bindings`.
- Given a domain filter: only bindings in that domain are compared; bindings in other domains are ignored.
- Given a user with no memberships and no Casbin bindings: `in_sync` is `True`.
- Prior art: existing command tests in the codebase that mock repositories and verify return values.

**`SyncFixCommand`**
- Given an orphan Casbin binding: it is removed and appears in `removed_from_casbin`; a `membership.deleted` event is published.
- Given a missing Casbin binding: it is added and appears in `added_to_casbin`; a `membership.created` event is published.
- Given a fully synced user: no changes are made, `events_published` is 0.
- Given multiple discrepancies: all are resolved in one call; `events_published` equals the total number of changes.
- Prior art: `CreateMembershipCommand` and `DeleteMembershipCommand` tests for the event publishing pattern.

**`SyncRouter`** (integration-level)
- `POST /sync/check` with a valid admin token and a synced user: returns 200 with `in_sync: true`.
- `POST /sync/check` with a valid admin token and a drifted user: returns 200 with discrepancies populated.
- `POST /sync/fix` with a valid admin token: returns 200 with changes applied.
- `POST /sync/check` and `POST /sync/fix` with a non-admin token: returns 403.
- Prior art: existing router integration tests for `authorization` and `membership` endpoints.

## Out of Scope

- Sync of Casbin `p` rules (policies: role → object/action) against DB permissions. Only `g` rules (role bindings: user → role) are in scope.
- Batch sync across all users. Both endpoints operate on a single user at a time.
- Automated or scheduled reconciliation (e.g., a cron job calling `/sync/fix` periodically).
- Dry-run mode for `/sync/fix`.
- Sync for any entity other than users (e.g., service accounts or roles themselves).

## Further Notes

- **Root cause of the immediate bug**: `app/routers/membership.py` calls `DeleteMembershipCommand.execute(domain=None)`. Memberships created via the standard flow default to `domain="*"`, so the Casbin binding lives in the `"*"` domain. Passing `domain=None` to `remove_role()` causes the enforcer to attempt a global (non-domain) removal which does not touch the domain-scoped binding. The fix is to pass `membership.domain` from the membership record to the delete command.
- The membership model explicitly documents that memberships are a "cache" and may have inconsistent data. The sync endpoints are the long-term tooling for managing this known inconsistency.
- `CasbinRepository.get_user_roles(user_id, domain)` only returns roles for one domain at a time. To retrieve bindings across all domains for a user, `SyncCheckCommand` will need to call `enforcer.get_filtered_grouping_policy(0, user_id)` directly, which returns all g rules where the subject matches.
