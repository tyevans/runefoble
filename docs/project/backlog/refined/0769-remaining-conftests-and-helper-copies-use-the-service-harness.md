---
id: '0769'
title: Remaining Conftests and Helper Copies Use the Service Harness
status: Refined
created: 2026-11-17
dependencies:
- TASK-0697
governing_adrs:
- ADR-0014
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---

# TASK-0769: Remaining Conftests and Helper Copies Use the Service Harness

## Status
Refined. Second slice of TASK-0697 (see `.audit/work/0697.md`, "Remaining split").

## Summary
TASK-0697 added the service harness registry and moved the root conftest and 18 group-1 conftests
to it. Groups 2 and 3, and the helper copies in test modules, still set seams by hand.

## Problem Statement
- G2 (verifier or client only): `tests/test_blackbox_character_sheet_ui`,
  `test_blackbox_cinematic_director`, `test_blackbox_rules_compendium_ui`, `test_blackbox_uvtt_import`,
  `test_character_sheet_models_modular_decomposition` (each `conftest.py`).
- G3 (own fixture names, mixed setters): `test_blackbox_faction_resources`,
  `test_blackbox_uvtt_doors_lights`, `test_blackbox_campaign_and_lobby`, `test_blackbox_west_marches_ui`,
  `test_blackbox_soundscape_ui`, `test_blackbox_campaign_atlas`, `test_blackbox_wardrobe_gallery`.
- Test-module copies: 17 `_trust_signing_issuer`, 20 `clean_environment`, 8 `assert_*_event`, and
  test-body `set_spicedb_client` and `set_event_bus` calls in about 25 test files.

## Documentation & Architecture Review
- ADR-0014: frontdoor setup. ADR-0015: no hidden fallbacks.
- The harness how-to that TASK-0697 wrote.

## Product & User Story References
None. Test infrastructure.

## Detailed Specification & Implementation Plan
1. Move G2 and G3 conftests to the harness registry. Delete their hand-written setters.
2. Replace the test-module helper copies with one helper each in `tests/helpers/`.
3. Replace test-body setter calls with harness fixtures. Every seam that a test changes is restored.
4. Tasks 0714 to 0717 depend on this; note in each what is now done.

## Frontdoor Blackbox Test Plan
- Run each changed directory in two orders in one run. Assert the same result.

## Definition of Done
- No conftest or test module sets a service seam by hand.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `work/0697.md`, `reports/refactor-r1/tests.md`
