---
id: '0625'
title: Remove Hardcoded SpiceDB Preshared Key Defaults and Fix the Wrong Setting Name
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0005
governing_prds: []
governing_stories: []
target_release: 0.9.0
---

# TASK-0625: Remove Hardcoded SpiceDB Preshared Key Defaults and Fix the Wrong Setting Name

## Status
Complete

## Summary
Several services send a SpiceDB preshared key that is a literal in code, and some read a setting name that does not exist. The rules-compendium service always sends `"secret"` because it reads `spicedb_token`, which is not a field on `PlatformSettings`. Remove every literal fallback, read one setting (`spicedb_preshared_key`), and fail at startup when it is missing outside test mode.

## Problem Statement
- `services/rules_compendium/src/rules_compendium/dependencies.py:51`: `token=getattr(settings, "spicedb_token", "secret")`. The field is `spicedb_preshared_key` (`libs/runefoble_platform/src/runefoble_platform/config.py`). Tests pass only because `MockSpiceDBClient` is injected (`w2-rules-compendium.md` F3). Same pattern in asset_forge, board_state, campaign_lore, soundscape dependencies.
- `services/campaign_lore/src/campaign_lore/dependencies.py:75`: literal `"secret"` fallback (`w2-campaign-lore.md` F16).
- `libs/runefoble_auth/src/runefoble_auth/spicedb.py:29-30`: default `runefoble_secret_key`.
- `libs/runefoble_auth/src/runefoble_auth/bootstrap_schema.py:61`: default `"secret"` (`w1-libs.md` F12).
- `services/audience_studio/src/index.ts:10` and `src/auth.ts:294,386`: literal `runefoble_secret_key` fallback (`w2-audience-studio.md` F13).
- `services/audience_studio/src/auth.ts` `SPICEDB_PRESHARED_KEY` is set in Helm (`audience-studio.yaml`), but the code path that uses it is dead (TASK-0439 scope).

## Documentation & Architecture Review
- `docs/reference/platform-services.md` documents `RUNEFOBLE_SPICEDB_PRESHARED_KEY`. Keep that name as the single source; state that there is no default outside tests.
- ADR-0001 (SpiceDB): preshared key is an operator secret, not a code constant.
- Frontdoor auth docs: `docs/how-to/define-spicedb-zanzibar-permissions.md` mentions the key; update.

## Product & User Story References
- None beyond ADR-0001. Platform-level security hygiene.

## Detailed Specification & Implementation Plan
1. Remove the literal defaults in `libs/runefoble_auth/src/runefoble_auth/spicedb.py` and `bootstrap_schema.py`. Read `RUNEFOBLE_SPICEDB_PRESHARED_KEY` only. If missing and not in test mode, raise `ConfigurationError` (existing error hierarchy in `runefoble_platform`).
2. Replace every service `getattr(settings, "spicedb_token", ...)` and literal `"secret"` with `settings.spicedb_preshared_key`. Grep: `grep -rn '"secret"\|runefoble_secret_key\|spicedb_token' services gateway libs --include='*.py'` must return only test files.
3. Audience-studio TypeScript: read `RUNEFOBLE_SPICEDB_PRESHARED_KEY` from the environment; throw at startup when missing unless `NODE_ENV=test`.
4. Keep Helm rendering of the key as is in this task (TASK-0626 moves it to a Kubernetes Secret).
5. Tests: set the key in the test conftest environment instead of relying on defaults.

## Frontdoor Blackbox Test Plan
- Before fix: a live SpiceDB test (existing `live_spicedb_endpoint` fixture) writes a homebrew rule through `POST /api/v1/compendium/homebrew` and the rules-compendium service sends the wrong key, so the call fails when SpiceDB enforces the Helm key.
- After fix: the same request with the Helm key succeeds. Starting a service with the key unset exits non-zero with a message naming `RUNEFOBLE_SPICEDB_PRESHARED_KEY`. Tests in `tests/test_blackbox_spicedb_preshared_key.py` check both through HTTP and process exit.

## Definition of Done
1. Grep check above returns no production literal key.
2. Each service with SpiceDB reads the one setting.
3. Startup fails with no key outside test mode, verified for at least rules-compendium and audience-studio.
4. Live SpiceDB blackbox test passes.
5. `uv run pytest` and `pnpm run build` pass.
6. No file above 500 lines.

## Audit Provenance

- Severity: high
- Source audits: `w2-rules-compendium.md`, `w2-campaign-lore.md`, `w1-libs.md`, `w2-audience-studio.md`, `w2-asset-forge.md`, `w2-campaign-analytics.md`, `w2-soundscape.md`, `w1-board-state.md`
