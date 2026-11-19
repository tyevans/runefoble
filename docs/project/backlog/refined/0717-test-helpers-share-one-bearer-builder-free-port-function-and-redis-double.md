---
id: '0717'
title: Test Helpers Share One Bearer Builder, Free-Port Function and Redis Double
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0717: Test Helpers Share One Bearer Builder, Free-Port Function and Redis Double

## Status
Refined. Found by the refactor audit round r1 and checked against the code by the orchestrator.

## Summary
About 90 test modules define their own bearer-header helper. Seven helpers find a free port. Two files define `MockAsyncRedis`. A fixture alias stays in the suite.

## Problem Statement
- Bearer copies: `tests/test_blackbox_board_state.py:14`, `tests/test_blackbox_print_forge.py:25`, `gateway/api/tests/test_gateway_auth.py:23`, and helpers `tests/helpers/campaign_analytics_service.py:38`, `tests/helpers/audience_server.py:38`, `tests/helpers/leitmotif_fixtures.py:21`, `tests/helpers/voice_identity.py:22`. The text `"Bearer {"` appears 515 times.
- Free-port copies: `tests/helpers/live_services.py:21`, `watcher_double.py:21`, `postgres.py:20`, `spicedb.py:30`, `audience_server.py:83`, `tests/test_blackbox_dev_environment.py:32`, `tests/test_blackbox_deployability_images.py:74`.
- `tests/test_redis_streams.py:13` defines a second `MockAsyncRedis`. The canonical one is `tests/helpers/mock_redis.py:17`.
- `tests/test_blackbox_settlements_integration/conftest.py:83` defines `client = session_client`, an alias.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0014.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add `bearer_headers(sub, issuer=SIGNING_ISSUER)` to `tests/helpers/ws_identity.py`. Replace the local copies and delete them. Do the helper modules and the files named above. Record the count left for a follow-up.
2. Export one `find_free_port()` and one `serve(app, lifespan=...)` from `tests/helpers/live_services.py`. Replace `serve_watcher_double` and the other copies.
3. Delete the second `MockAsyncRedis`. Move any missing behaviour into the helper. Coordinate with TASK-0351.
4. Rename call sites from `client` to `session_client` and delete the alias. TASK-0697 may own the conftest edit: if so, skip steps that touch the same lines.

Refactor round 2 addendum (2026-11-18): Voice identity aliases: `tests/helpers/voice_identity.py:20` (`VOICE_SIGNING_ISSUER = SIGNING_ISSUER`) is a re-export alias. `voice_auth_headers` (`:23`) duplicates `bearer` in `tests/helpers/ws_identity.py:16`. `voice_ws_subprotocols` (`:28`) duplicates `ws_subprotocols` (`:21`). Delete the alias and both voice helpers. Callers use the `ws_identity` helpers.

Counts from the audit (recounted): `def _auth(` appears in 40 files under `tests/` and `gateway/api/tests/`. The text `Bearer {` appears 470 times in those folders.

## Frontdoor Blackbox Test Plan
- The affected suites pass unchanged.
- `grep -rn "def _free_port\|def get_free_port\|def find_free_port" tests` shows one definition.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Refactor r3 Addendum (Detailed Specification step 1)

Refactor r3 addendum (2026-11-19): 40 local `_auth`, `_bearer`, `bearer_token`, `bearer_for` or `bearer_headers` helpers in 35 files under `tests/` wrap `issuer.mint(sub)`. Examples: `tests/test_blackbox_compendium_authz.py:44`, `tests/test_blackbox_campaign_grants_authz.py:28`, `tests/test_blackbox_character_authz.py:35`, `tests/test_blackbox_session_chronicle.py:40`. Replace each with `bearer(sub, issuer)` from `tests/helpers/ws_identity.py:16`. The username-claim copy at `tests/test_blackbox_campaign_member_names.py:17` calls `issuer.mint` with `extra_claims` directly. List the 35 files in this task before work starts (`grep -rln "def _auth\|def _bearer\|def bearer_token\|def bearer_for\|def bearer_headers" tests/`).

## Audit Provenance
- Severity: low
- Source audits: `refactor-r1/tests.md`
