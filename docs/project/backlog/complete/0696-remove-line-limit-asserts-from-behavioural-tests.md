---
id: '0696'
title: Remove Line-Limit Asserts From Four Behavioural Test Modules
status: Complete
created: 2026-11-17
dependencies:
- TASK-0681
governing_adrs:
- ADR-0017
governing_prds: []
governing_stories: []
target_release: 0.9.0
severity: low
source_audits:
- work/0681.md
---

# TASK-0696: Remove Line-Limit Asserts From Four Behavioural Test Modules

## Status
Complete

## Summary
Four test functions check a behaviour and also assert source line counts. The line-limit part is structural. ADR-0017 owns the file length invariant, and the health gate owns its check. This task keeps the behavioural part and deletes the line-limit asserts.

## Problem Statement
- `tests/test_blackbox_asset_forge_generation.py::test_raster_modular_decomposition_and_line_limits`
- `tests/test_blackbox_bulletin_board/test_bulletin_posting.py::test_blackbox_bulletin_board_manifest_and_components`
- `tests/test_blackbox_merchant_haggling/test_bargain_flow.py::test_blackbox_merchant_haggling_manifest_and_components`
- `tests/test_blackbox_minigames_suite.py::test_minigames_suite_manifest_and_file_invariants`

## Documentation & Architecture Review
- ADR-0017: file length is an invariant enforced by the health gate, not by feature tests.
- ADR-0014: feature tests use frontdoors. A manifest route check is allowed only as a public route check.

## Product & User Story References
None. Test hygiene.

## Detailed Specification & Implementation Plan
1. In each function, keep the frontdoor behaviour (a public route call and its response). Delete the line-count and file-existence asserts.
2. If the function name refers to a structural check, rename it to name the behaviour.
3. Do not add a replacement structural check.

## Frontdoor Blackbox Test Plan
- Each renamed test still calls its public route and asserts the observable response.
- No test reads source files or counts lines after this change.

## Definition of Done
- No line-count or file-existence assert remains in the four functions.
- `uv run pytest` and `make lint` pass.
