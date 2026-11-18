---
id: '0528'
title: Services Verify Zitadel Tokens (asset_forge, soundscape, character_sheet)
status: Complete
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0536
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0007
governing_prds:
- PRD-0006
- PRD-0009
- PRD-0010
governing_stories:
- US-0013
target_release: 0.9.0
severity: critical
source_audits:
- w2-asset-forge.md
- w2-soundscape.md
- w1-character-sheet.md
- w3-authz-coverage.md
---

# TASK-0528: Services Verify Zitadel Tokens (asset_forge, soundscape, character_sheet)

## Status
Complete

## Summary
Three more contexts trust a header for identity. Asset forge writes assets as `anonymous_creator` when no identity exists. Soundscape and character sheet skip checks when the header is missing. Apply the verified principal to each router and remove the anonymous fallbacks.

## Problem Statement
- `services/asset_forge/src/asset_forge/dependencies.py:87-90` returns the raw `x-user-id` header. Audit w2-asset-forge F4.
- Asset forge writes `creator` and `campaign` relations inside `contextlib.suppress(Exception)`, and falls back to `anonymous_creator` or `anonymous_crafter` as the creator id (audit w2-asset-forge F4). The suppress is an authorization defect and belongs to the authorization theme. The anonymous fallback is an identity defect and is fixed here.
- `services/soundscape/src/soundscape/dependencies.py:107-110` returns the header. `check_user_can_control_soundscape` returns `True` when `user_id` is empty (lines 121-122). Audit w2-soundscape. Routes `tension.py:69`, `stems.py:60`, and `stems.py:166` have no check at all.
- `services/character_sheet/src/character_sheet/dependencies.py` `authorize_character_edit` runs the check only `if user_id and ...` (audit w1-character-sheet F2). About 20 routes in `router.py` take no identity at all.

## Documentation & Architecture Review
- Same pattern as TASK-0527: the service verifies the token. The gateway forwards it (TASK-0536).
- Character sheet also has an in-memory gateway store (audit w1-character-sheet F1). That is a separate wiring defect. This task does not change it.
- Creation ownership writes in character sheet (`router.py:27,32`, `suppress(Exception)`) are an authorization defect. Note them in the PR for the authorization theme.

## Product & User Story References
- PRD-0006 (character sheet), PRD-0009 (asset forge), PRD-0010 (soundscape). US-0013 for the verified-subject rule.

## Detailed Specification & Implementation Plan
1. Add the issuer, audience, and JWKS settings to each service's platform settings.
2. Replace each `get_current_user_id` with the `require_principal`-based dependency. Apply it to every router.
3. Delete all reads of `x-user-id`. Confirm with `grep -rn -i "x-user-id" services/asset_forge services/soundscape services/character_sheet --include=*.py`.
4. Remove the `anonymous_creator`, `anonymous_crafter`, and similar literals. Creation routes use `principal.user_id`.
5. Change helper signatures to `user_id: str` and delete `if not user_id` returns in the touched files.
6. Character sheet: apply the identity dependency to every route in `router.py` and `wardrobe_router.py` and `crafting_router.py`. Mutations and reads both require a verified subject.
7. Helm: add the issuer, audience, and JWKS variables to the three service templates. Coordinate with TASK-0624 and TASK-0620.

## Frontdoor Blackbox Test Plan
HTTP tests through `TestClient` with signing-issuer tokens.
- Before: `POST /api/v1/forge/token` with no identity returns 200 and creates an asset owned by `anonymous_creator`. `PUT /api/v1/characters/{id}/guardrails` with no identity returns 200.
- After:
  - No bearer, garbage bearer, and forged token return 401 on every route in the three services.
  - A forged `x-user-id` header is ignored. The created asset's creator equals the token `sub`.
  - `/health` and `/openapi.json` stay public.

## Definition of Done
1. `grep -rn "anonymous_creator\|anonymous_crafter\|x-user-id" services/asset_forge services/soundscape services/character_sheet --include=*.py` returns no production matches.
2. Service suites pass with the signing issuer.
3. Helm renders the new variables.
4. The three service how-tos show a bearer token.
5. `uv run ruff check` passes for the three services. No file exceeds 500 lines.
