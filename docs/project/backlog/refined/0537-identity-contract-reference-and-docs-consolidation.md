---
id: '0537'
title: Identity Contract Reference, Auth Docs Consolidation, and Changelog
status: Refined
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0521
- TASK-0522
- TASK-0523
- TASK-0526
- TASK-0527
- TASK-0528
- TASK-0529
- TASK-0530
- TASK-0531
- TASK-0532
- TASK-0533
- TASK-0534
- TASK-0536
governing_adrs:
- ADR-0005
- ADR-0007
governing_prds:
- PRD-0023
governing_stories:
- US-0062
target_release: 0.9.0
severity: medium
source_audits:
- w3-docs-integrity.md
- w1-libs.md
- w1-gateway-api.md
---

# TASK-0537: Identity Contract Reference, Auth Docs Consolidation, and Changelog

## Status
Refined

## Summary
After the identity tasks land, one reference page must state the full identity contract for every surface. Several docs still describe dev mode, `x-user-id`, mock tokens, and removed routes. Write the reference, correct the stale pages, and record the change in the changelog.

## Problem Statement
- `docs/how-to/authenticate-with-zitadel-oidc.md` describes dev mode (audit w1-libs F17). TASK-0520 rewrites the dev sections. This task checks the whole page.
- `docs/how-to/manage-secret-dm-traps-and-map-triggers.md` and other how-tos use `x-user-id` in examples (audit w1-board-state F15).
- `docs/reference/ports-and-endpoints.md` and `docs/reference/platform-services.md` list removed routes and environment variables (audit w3-docs-integrity PS2 and the route-table audit).
- `docs/reference/spicedb-zitadel-identity-sync.md` describes the claim sync that TASK-0534 removes.
- There is no single reference for the identity contract. Generic patterns need one (DoD item 4).

## Documentation & Architecture Review
- Diataxis: a reference page for the contract (`docs/reference/identity-and-token-contract.md`, new). How-to pages for tasks. Explanation is not needed here.
- Keep each page accurate to the code. Check each page against the code after the tasks land.

## Product & User Story References
- PRD-0023 and US-0062 (identity).

## Detailed Specification & Implementation Plan
1. Create `docs/reference/identity-and-token-contract.md` with these sections:
   - Token issuer, audience, and JWKS (the three variables and what each one means).
   - Surface rules: HTTP `Authorization: Bearer`; WebSocket subprotocol `runefoble.bearer.<jwt>` with `runefoble.v1`; service-to-service service token for the Inference Worker.
   - Subject: `sub` is the user id. Roles and admin flags are not identity.
   - Public routes (health, OpenAPI, Swagger, manifests). Nothing else is public.
   - Error shape and status (401 for refused credentials, 502 for upstream failure).
   - Removed routes and their replacements (token issue, refresh, logout, seed, invite, sync/user, dev mail).
2. Correct `docs/how-to/authenticate-with-zitadel-oidc.md` end to end.
3. Replace `x-user-id` examples in how-tos with bearer examples. Use `grep -rln "x-user-id\|X-User-Id" docs` to find them.
4. Update `docs/reference/ports-and-endpoints.md`, `docs/reference/platform-services.md`, and `docs/reference/spicedb-zitadel-identity-sync.md`.
5. `CHANGELOG.md` `[Unreleased]`: record the dev mode removal, the removed routes, the new token rules, and the new config variables (Keep a Changelog format).
6. `docs/marketing.md`: update the security status line if the page claims an auth feature that is now true.

## Frontdoor Blackbox Test Plan
Documentation checks.
- Before: the grep returns matches in docs. The reference page does not exist.
- After:
  - `grep -rn "x-user-id\|X-User-Id\|dev-user-001\|runefoble-dev-signature\|sync/user" docs` returns no matches outside historical records.
  - Every route named in the reference exists in `/openapi.json` or is listed as removed.
  - The links from the how-to index resolve.

## Definition of Done
1. The reference page exists and matches the code.
2. The grep above is clean.
3. `CHANGELOG.md` has the entry.
4. Links check passes (existing docs link checker or manual check).
5. No file exceeds 500 lines.

## Orchestrator Addenda (2026-11-17, round 2)

Source: `.audit/synth/discovered-round2.md`.

- docs/how-to/verify-identity-in-fastapi-and-websockets.md:23 uses issuer http://zitadel:8080. Use the browser-facing issuer from the chart, as the authentication guide does.
