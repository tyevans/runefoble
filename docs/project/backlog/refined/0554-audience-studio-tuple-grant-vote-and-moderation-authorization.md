---
id: '0554'
title: Audience Studio Tuple Grant, Vote, and Moderation Authorization
status: Refined
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0625
- TASK-0533
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0011
governing_stories:
- US-0031
- US-0029
- US-0030
target_release: 0.9.0
severity: critical
source_audits:
- w2-audience-studio.md
---

# TASK-0554: Audience Studio Tuple Grant, Vote, and Moderation Authorization

## Status
Refined

## Summary
The audience studio is a TypeScript service. Any caller can write a `dungeon_master` tuple for itself through a public route, then approve chaos modifiers. Votes, reads, and WebSocket actions have no check. The acting user comes from the request body or a header, with a `dm-user` fallback. The service keeps its own copy of the role hierarchy and never calls SpiceDB in deployment. This task removes the public tuple write, binds each action to the `audience_poll` permissions in the schema, and uses one real SpiceDB client.

## Problem Statement
- `services/audience_studio/src/routes.ts:213-237` (`POST /auth/tuples`): no authentication. Live run: a caller granted `mallory` `dungeon_master` (201). Then `POST /proposals/{id}/approve` with `dm_user_id: mallory` returned 200 (`w2-audience-studio.md` F1).
- `routes.ts:168-171` and `:195-198`: the acting user comes from the body (`dm_user_id`) or the `x-user-id` header, with a `'dm-user'` fallback.
- `routes.ts:92-124` (`POST /polls/:id/votes`): no check. `voter_id` is client-supplied and dedupes ballots (`src/pollEngine.ts:131-135`).
- `routes.ts:67-89` and `:143-156` (`GET /polls`, `GET /proposals`): no check. Proposal parameters are visible to anyone.
- `src/websocket.ts:45-70`: any client connects to `/ws/audience/:campaignId` and receives all broadcasts, including `proposal_queued`. `:94-120` (`cast_vote`, `approve_proposal`, `veto_proposal`) take `userId` from the message. The stored `role` (`:85-86`) is never checked (`w2-audience-studio.md` F3).
- `src/auth.ts:334-377` hardcodes the role names and the campaign hierarchy. This copies the schema into TypeScript (`w2-audience-studio.md` F2, AGENTS.md Hard Invariant 1).
- `src/auth.ts:380`: SpiceDB is called only when the endpoint starts with `http`. Helm sets `RUNEFOBLE_SPICEDB_ENDPOINT=spicedb:50051` with no scheme, so the live path is dead.
- `src/routes.ts:180` and `:207` choose HTTP 403 by searching error text for `dungeon_master`. An unknown proposal returns 400 (`w2-audience-studio.md` F13).
- The fallback key literal is removed by TASK-0625.

## Documentation & Architecture Review
- ADR-0001: `audience_poll.view` for reads, `audience_poll.vote` for votes, `audience_poll.approve` and `audience_poll.veto` for moderation. The schema already defines these permissions (`libs/runefoble_auth/schema/runefoble.zed`, `definition audience_poll`).
- ADR-0007: the audience context owns poll and proposal state. The audience context does not own roles. Roles are schema relations.
- ADR-0014: TypeScript tests use the public HTTP and WebSocket surfaces. The in-memory tuple store is not a test backdoor.
- `docs/how-to/orchestrate-audience-chaos-polls.md` describes these routes. It also describes features that do not exist (`w2-audience-studio.md` F8). Fix the parts this task changes.
- TASK-0439 (proposed, gateway Zanzibar proxy) names permissions that do not exist (`can_manage_audience_polls`, `can_approve_audience_chaos`). That task must be corrected before it is refined (see the index report).

## Product & User Story References
- US-0031 (live stream audience chaos polls and rumors). US-0029 (spectator cinematic camera). US-0030 (OBS overlay). PRD-0011 (spectator studio and audience interactivity).

## Detailed Specification & Implementation Plan
1. TASK-0533 removes `POST /auth/tuples` and the identity fallbacks. Confirm both are gone before this task starts.
2. Identity: use the verified principal that TASK-0533 provides. Do not add a second verifier or a second header parser.
3. SpiceDB: one client that connects to the configured endpoint. The endpoint setting is `host:port` for gRPC, or an explicit `grpc://` or `https://` scheme. The client reads the preshared key from `RUNEFOBLE_SPICEDB_PRESHARED_KEY` (TASK-0625). Delete `src/auth.ts` role hierarchy and the `http` branch.
4. Permission per action:
   - `GET /polls`, `GET /polls/:id`, `GET /proposals`: `audience_poll.view` on the poll's campaign. Proposal parameters are sent only to principals with `audience_poll.approve`. Other callers get the proposal title and status.
   - `POST /polls/:id/votes`, `cast_vote`: `audience_poll.vote`. The voter is the principal.
   - `approve`, `veto` (HTTP and WebSocket): `audience_poll.approve` and `audience_poll.veto`.
5. WebSocket (`src/websocket.ts`): connect requires the principal and `audience_poll.view`. Broadcasts of `proposal_queued` go only to sockets with `audience_poll.approve`.
6. Errors: typed errors `NotFound` (404), `Forbidden` (403), and `Unauthenticated` (401). Map SpiceDB unavailability to 503. Remove text matching.
7. Remove the Helm env value that is not used after this change. Keep the key env value (TASK-0625 owns it).

## Frontdoor Blackbox Test Plan
Setup: campaign and poll are created through the audience routes. Roles are set through the campaign role route (TASK-0543), using a real SpiceDB test container (`live_spicedb_with_schema` equivalent for the TypeScript test runner).
- Before the fix, `POST /auth/tuples` with `dungeon_master` for a stranger returns 201. After the fix the route returns 404.
- A stranger calls `POST /proposals/{id}/approve`: 401 without a principal, 403 with a player principal. Before the fix it returns 200.
- A spectator reads `GET /proposals`: parameters are absent from the response.
- A player votes twice with different `voter_id` values in the body: the server uses the principal, so the second vote is rejected as a duplicate.
- A WebSocket connect without a principal is refused.
- A stubbed SpiceDB outage returns 503 on a read.

## Definition of Done
1. Blackbox tests exist in `services/audience_studio/tests/` (or the existing TypeScript test folder) and pass against the live SpiceDB container.
2. `src/auth.ts` contains no role-name hierarchy and no `dm-user` fallback.
3. `POST /auth/tuples` does not exist.
4. `grep -rn "dm-user\|runefoble_secret_key" services/audience_studio/src` returns nothing.
5. `pnpm --filter` build and tests for `services/audience_studio` pass. Use the package scripts that exist in the package.
6. The how-to doc is updated for the routes that changed.
7. No file in the change exceeds 500 lines. Split `routes.ts` by route group if it grows past the limit.
