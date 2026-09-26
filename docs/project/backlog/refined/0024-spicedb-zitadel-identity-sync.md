---
id: 0024
title: SpiceDB Zanzibar Relationship Synchronization with Zitadel OIDC Identities
status: Refined
created: 2026-09-25
dependencies: [TASK-0008, TASK-0016]
governing_adrs: [ADR-0001, ADR-0005, ADR-0007]
target_release: 0.2.0
---

# TASK-0024: SpiceDB Zanzibar Relationship Synchronization with Zitadel OIDC Identities

## Status
Refined

## Summary
Implement automated relationship tuple synchronization between Zitadel OIDC identities/roles and SpiceDB Zanzibar schema (`libs/runefoble_auth/schema/runefoble.zed`). As the primary foundational enabler for Milestone 2 (Live Collaborative Alpha), this bridge ensures that users authenticated via Zitadel JWT tokens are automatically provisioned with the correct object-level permissions (e.g. campaign GM, campaign player, character owner, session spectator) in SpiceDB without manual administrator intervention.

## Problem Statement & Architectural Context
Hard Invariant 1 dictates that all object-level authorization runs through SpiceDB Zanzibar schema rather than ad-hoc role checks in business logic. While `libs/runefoble_auth` provides Zanzibar permission checking clients and gateway middleware (`TASK-0008`, `TASK-0016`), the relationship tuples in SpiceDB are currently static or mock-populated during tests. In a production cluster running Zitadel and SpiceDB, changes in identity state (user registration, campaign creation, inviting a player, assigning character ownership, promoting a co-GM) must synchronize with SpiceDB relationship tuples.

## Governing Documents
- **ADRs**:
  - `ADR-0001`: SpiceDB Zanzibar Object Authorization
  - `ADR-0005`: Kubernetes-First Infrastructure with Helm and Kind
  - `ADR-0007`: Domain-Driven Design Architecture
- **Roadmap**: Milestone 2: Live Collaborative Alpha (SpiceDB production cluster syncing with Zitadel OIDC identities)
- **User Stories**: `US-0008`, `US-0010`

## Scope of Work
1. **Zitadel-to-SpiceDB Synchronization Service (`libs/runefoble_auth/src/runefoble_auth/sync.py`)**:
   - Provide `ZitadelSpiceDBSyncService` which translates identity events and user claims into Zanzibar relationship tuples:
     - `campaign:<id>#gm@user:<sub_id>`
     - `campaign:<id>#player@user:<sub_id>`
     - `campaign:<id>#spectator@user:<sub_id>`
     - `character:<char_id>#owner@user:<sub_id>`
     - `character:<char_id>#campaign@campaign:<id>`
     - `session:<sess_id>#campaign@campaign:<id>`
   - Support batch writes, idempotency, and reconciliation checks against SpiceDB client.
2. **Public Sync Endpoints (`gateway/api/src/gateway_api/auth_sync.py`)**:
   - Expose frontdoor HTTP endpoints:
     - `POST /api/v1/auth/sync/user`: Syncs Zitadel user claims into SpiceDB identity mappings.
     - `POST /api/v1/auth/sync/membership`: Grants/revokes campaign or session roles (`gm`, `player`, `spectator`) for a given user.
     - `POST /api/v1/auth/sync/character-ownership`: Binds character aggregate to owning user and parent campaign.
     - `GET /api/v1/auth/sync/health`: Reports synchronization state and SpiceDB connectivity.
3. **Domain Event Listeners**:
   - Subscribe to `SessionCreated`, `ParticipantJoined`, and `CharacterCreated` events on Redis Streams, automatically ensuring corresponding SpiceDB relationship tuples exist before action mutators can execute.
4. **Resilience & Fallback**:
   - Resilient retry handling when SpiceDB or Zitadel is briefly unreachable.
   - Maintain in-memory / mock synchronization driver for offline local and CI testing.

## Definition of Done (Hard Invariant 7: Blackbox TDD Frontdoor Setup)
1. **Frontdoor Blackbox Verification**:
   - All tests interact strictly through public HTTP endpoints (`/api/v1/auth/sync/*`) or published domain events on the event bus.
   - Zero backdoor state injection into private class attributes or mock dictionaries.
2. **Permission Check Assertion**:
   - Tests assert observable authorization outcomes by querying `SpiceDBClient.check_permission` and authenticated gateway endpoints (`POST /api/v1/sessions/...`, `POST /api/v1/board/tokens/...`):
     - Synchronized GM can execute DM override and update campaign atmosphere.
     - Synchronized Player can move their own character token, but is denied moving another player's token.
     - Spectator has read-only scene visibility and is rejected when attempting token mutation.
3. **Idempotence & Revocation**:
   - Re-syncing the same membership or claims produces no duplicate relationships or errors.
   - Revocation endpoint removes Zanzibar relationship and immediately revokes permissions in subsequent checks.
4. **Code Quality & Invariants**:
   - All new files < 500 lines (Hard Invariant 6).
   - 100% pass on `uv run pytest` and clean `uv run ruff check .`.
   - Updated Diataxis reference documentation under `docs/reference/` describing Zitadel-SpiceDB sync flow.
