---
id: '0742'
title: User Profile Attributes Have a Durable Owner Behind the Gateway
status: Refined
created: 2026-11-17
dependencies:
- TASK-0488
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds:
- PRD-0023
governing_stories:
- US-0062
- US-0070
target_bc: game_session
target_release: 0.9.0
---
# TASK-0742: User Profile Attributes Have a Durable Owner Behind the Gateway

## Status
Refined. Found by the refactor audit round refactor-r1 and checked against the code on 2026-11-17.

## Summary
`GET` and `PATCH /api/v1/profile` serve from a dict in the gateway process. Profile edits are lost on every gateway restart, and a second replica has other data. ADR-0015 (a) and (b) say the gateway holds no domain state.

## Problem Statement
- `gateway/api/src/gateway_api/routers/auth/profile.py:15` declares `USER_PROFILES: dict[str, dict[str, Any]] = {}`.
- `profile.py:27-45` (`get_stored_profile`) calls `setdefault` on that dict. `profile.py:54` and `:83` serve the two routes from it.
- No refined or proposed task names this file or `USER_PROFILES`. TASK-0488 notes coordination with TASK-0521 and TASK-0523. Those tasks are not in `refined/` or `proposed/`: confirm their status.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011, ADR-0015.
- ADR-0015 (a): campaign lifecycle and membership belong to game_session. This task places profile attributes there too, because it already owns user-to-campaign membership. `docs/how-to/manage-campaign-lifecycle-and-invites.md`, `docs/how-to/call-owning-services-through-the-gateway.md`.
- Add a how-to or reference entry for the profile route and event.

## Product & User Story References
- PRD-0023
- US-0062
- US-0070

## Detailed Specification & Implementation Plan
1. Add a `UserProfileAggregate` in game_session (`DeclarativeAggregate`, `@handles`, `AggregateRepository`) with events `ProfileUpdated` registered in `runefoble_events`. Key it by the Zitadel subject.
2. Add owner routes `GET` and `PATCH /api/v1/profile` in game_session. Verify the principal in the service (ADR-0015 c).
3. Replace the gateway router body with `forward_json`. Delete `USER_PROFILES` and `get_stored_profile`. Keep the response shape the App Shell reads today.
4. TASK-0488 removes the camelCase aliases on `UpdateProfileRequest`: do not touch them here.

## Frontdoor Blackbox Test Plan
- Through the gateway with a Zitadel token: `PATCH /api/v1/profile`, then `GET`. Assert the updated fields.
- Restart game_session (subprocess pattern, TASK-0698), then `GET`. Assert the fields persist.
- Without a token: 401.

## Definition of Done
- No profile state is in gateway memory. Reference doc lists the event.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: high
- Source audits: `gateway-api.md (F1)`
