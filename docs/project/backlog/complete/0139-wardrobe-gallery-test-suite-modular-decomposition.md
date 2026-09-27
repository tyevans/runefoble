---
id: 0139
title: Wardrobe Gallery Blackbox Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0124
governing_adrs:
- ADR-0013
governing_prds:
- PRD-0016
governing_stories:
- US-0055
target_release: 0.4.0
pr_url: https://github.com/tyevans/runefoble/pull/155
---
# TASK-0139: Wardrobe Gallery Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose the monolithic blackbox test suite `tests/test_blackbox_wardrobe_gallery.py` (415 lines, 83% of limit) into modular frontdoor test suites under `tests/test_blackbox_wardrobe_gallery/` (`test_wardrobe_api.py`, `test_wardrobe_conditions.py`, `test_wardrobe_events.py`), ensuring all test files remain < 200 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_wardrobe_gallery.py` has grown to 415 lines as tests were added for dynamic bloodied overlays, condition badges, generative Silo S3 variants, SpiceDB permissions, and CloudEvents dispatching. Splitting it into single-responsibility test modules prevents breaching Hard Invariant 6 (< 500 lines) and improves parallel test performance.

## Governing Architecture & ADRs
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Component test separation and frontdoor validation.

## Product & User Story References
- **Product Requirement**: [`prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md`](../../product/accepted/prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md)
- **User Story**: [`us-0055-dynamic-character-wardrobe-and-condition-portraits.md`](../../user_stories/accepted/us-0055-dynamic-character-wardrobe-and-condition-portraits.md)

## Detailed Specification & Implementation Plan
1. **API & Permission Tests (`tests/test_blackbox_wardrobe_gallery/test_wardrobe_api.py`)**:
   - Extract frontdoor REST tests for `/api/v1/characters/{id}/portrait` and `/wardrobe` with SpiceDB authorization checks (< 150 lines).
2. **Condition Overlay Tests (`tests/test_blackbox_wardrobe_gallery/test_wardrobe_conditions.py`)**:
   - Extract tests for HP threshold bloodied vignettes, poisoned auras, and stunned visual markers (< 150 lines).
3. **Event & Asset Storage Tests (`tests/test_blackbox_wardrobe_gallery/test_wardrobe_events.py`)**:
   - Extract CloudEvents validation (`CharacterDamaged`, `PortraitVariantGenerated`) and Silo S3 asset storage checks (< 150 lines).
4. **Test Shim (`tests/test_blackbox_wardrobe_gallery.py`)**:
   - Replace old file with a clean deprecation / runner shim or remove upon directory migration.

## INVEST Criteria Evaluation
- **Independent (I)**: Test organization change with zero production code impact.
- **Negotiable (N)**: Split boundaries between test modules can be adjusted.
- **Valuable (V)**: Protects codebase against Hard Invariant 6 breach and eases maintenance.
- **Estimable (E)**: Standard pytest test suite refactoring.
- **Small (S)**: Bounded strictly to `tests/test_blackbox_wardrobe_gallery.py`.
- **Testable (T)**: Validated by ensuring 100% of existing wardrobe gallery tests continue to pass.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Test Decomposition**:
   - Modular test directory `tests/test_blackbox_wardrobe_gallery/` created.
   - All resulting test files < 200 lines.
2. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_wardrobe_gallery/`.
   - Passes `uv run ruff check .` and `uv run ruff format --check .`.
