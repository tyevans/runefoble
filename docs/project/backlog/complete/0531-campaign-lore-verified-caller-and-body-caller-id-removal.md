---
id: '0531'
title: Campaign Lore Derives the Caller Only from the Verified Principal and Removes Body caller_id
status: Complete
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0536
governing_adrs:
- ADR-0001
- ADR-0007
governing_prds:
- PRD-0007
governing_stories:
- US-0013
target_release: 0.9.0
---

# TASK-0531: Campaign Lore Derives the Caller Only from the Verified Principal and Removes Body caller_id

## Status
Complete

## Summary
Lore search takes the caller from a request body field named `caller_id`. A player can send the DM id and read secret lore. Remove the body field. Apply the verified principal to every campaign-lore route. Keep the secret-visibility rule itself with the authorization theme.

## Problem Statement
- `services/campaign_lore/src/campaign_lore/routers/search.py:69` sets `user_id = req.caller_id or header_user_id`. The body wins. Audit w2-campaign-lore F2 (critical).
- Probe in the audit: a player sends `x-user-id: <player>` with body `caller_id: <dm>` and gets `can_read_secrets: True` with one secret chunk.
- `services/campaign_lore/src/campaign_lore/permissions.py:10-19` reads only the `x-user-id` header.
- Many campaign-lore routers (`atlas.py`, `codex/*`, `documents.py`, `handouts.py`, `relics.py`, `west_marches.py`) read the header or take no identity. Audit w2-campaign-lore, w3-authz route table rows 123-141.

## Documentation & Architecture Review
- The service verifies the token itself (same pattern as TASK-0527). The gateway forwards it (TASK-0536).
- Hardcoded SpiceDB token fallback in `dependencies.py:75` is handled by TASK-0625. Do not change it here.
- Codex entry cross-campaign access (audit w2-campaign-lore F1) is an authorization defect. Out of scope.
- `docs/reference` lists the lore search request schema. Update it when `caller_id` is removed.

## Product & User Story References
- PRD-0007 (lore and RAG). US-0013 for the verified-subject rule.

## Detailed Specification & Implementation Plan
1. Remove the `caller_id` field from `LoreSearchRequest`. The OpenAPI schema changes. Update the reference doc and the App Shell caller if it sends `caller_id` (grep the frontend).
2. Set `user_id = principal.user_id` in `search.py`. Delete `header_user_id`.
3. Replace `get_current_user_id` in `permissions.py` with the `require_principal`-based dependency. Apply it at router level to every campaign-lore router.
4. Delete every `x-user-id` read in the service. Confirm with `grep -rn -i "x-user-id\|caller_id" services/campaign_lore/src`.
5. Keep `/health`, `/openapi.json`, and `/ui/manifest` public.
6. Helm: add the three issuer variables to the campaign-lore template.

## Frontdoor Blackbox Test Plan
HTTP tests with `TestClient` and signing-issuer tokens.
- Before: a player sends `x-user-id: player` and body `caller_id: dm` to `POST /api/v1/lore/search`. The response includes the secret chunk.
- After:
  - The same request with the player token returns no secret chunks. The body `caller_id` is rejected or ignored (request schema has no such field, so the field is refused with 422 under strict validation).
  - Every campaign-lore route returns 401 with no bearer.
  - A DM token still receives the secret chunk, because the verified subject is the DM.

## Definition of Done
1. `grep -rn "caller_id" services/campaign_lore/src` returns no matches.
2. Campaign-lore suites pass with the signing issuer.
3. Reference docs for lore search show the new request shape.
4. Helm renders the variables.
5. No file exceeds 500 lines.

## Audit Provenance

- Severity: critical
- Source audits: `w2-campaign-lore.md`, `w3-authz-coverage.md`
