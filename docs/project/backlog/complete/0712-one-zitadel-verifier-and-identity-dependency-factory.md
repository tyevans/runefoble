---
id: '0712'
title: One Zitadel Verifier and Identity Dependency Factory
status: Complete
created: 2026-11-17
dependencies:
- TASK-0541
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0712: One Zitadel Verifier and Identity Dependency Factory

## Status
Complete

## Summary
Eleven modules copy the same Zitadel verifier getter and setter, and nine copy the same user-id helper. A library factory with explicit settings replaces all copies. The library default issuer is removed so that a missing setting fails loudly.

## Problem Statement
- Verifier copies: `services/asset_forge/src/asset_forge/dependencies.py:79`, `services/board_state/src/board_state/dependencies.py:71`, `services/campaign_analytics/src/campaign_analytics/dependencies.py:66`, `services/campaign_lore/src/campaign_lore/identity.py:20`, `services/character_sheet/src/character_sheet/dependencies.py:82`, `services/game_session/src/game_session/settlement/auth/tokens.py:24` (removed), `services/rules_compendium/src/rules_compendium/dependencies.py:67`, `services/soundscape/src/soundscape/dependencies.py:99`, `services/the_watcher/src/the_watcher/identity.py:19`, `services/voice_agent/src/voice_agent/auth.py:20`, `gateway/api/src/gateway_api/auth.py:58`.
- User-id helpers: nine modules, for example `board_state/dependencies.py:100` and `the_watcher/identity.py:42`.
- `libs/runefoble_auth/src/runefoble_auth/zitadel.py:74` defaults `issuer="http://localhost:8080"`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0001, ADR-0015.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add `libs/runefoble_auth/src/runefoble_auth/wiring.py` with `make_verifier_holder(build)` (get and set for tests) and `build_identity_dependencies(holder, credential)` returning `get_principal`, `CallerPrincipal`, `CallerId`, `get_caller_or_service`, `CallerOrService`.
2. The constructor takes explicit issuer, audience and internal URL. No default values.
3. Remove the `issuer` default in `ZitadelAuthService`.
4. Each service deletes its copy and calls the factory. Delete the user-id helpers and update callers. No alias remains.
5. Do this in one pass, one commit per service, so no merge leaves two patterns.
6. Sequence: run after TASK-0541 (SpiceDB factory). Coordinate with TASK-0546, 0551, 0555, 0556, which edit `get_current_user_id` callers.

## Frontdoor Blackbox Test Plan
- Existing `tests/test_blackbox_token_verifying_services.py` and `tests/test_blackbox_service_bearer_verification.py` pass unchanged.
- Per service: a request with no token returns 401. A request with a forged token returns 401.
- A service built with no issuer setting fails at start-up.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r1/libs.md`
