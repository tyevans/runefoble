---
id: '0114'
title: Theming Tokens and Contrast Invariants Test Suite Modular Decomposition
status: Refined
created: 2026-09-26
dependencies:
- TASK-0012
- TASK-0074
governing_adrs:
- ADR-0004
- ADR-0009
- ADR-0012
target_release: 0.3.0
governing_prds:
- PRD-0013
governing_stories:
- US-0016
- US-0041
- US-0042
---

# TASK-0114: Theming Tokens and Contrast Invariants Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_theming.py` (332 lines, 66.4% of limit) into two specialized test modules (`tests/test_theming_tokens.py` and `tests/test_theming_contrast.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as new component themes and broadcast overlay color tokens are added.

## Problem Statement
`tests/test_theming.py` currently spans 332 lines and validates multiple design system layers in a single test module:
1. CSS custom property tokens: Verifying Bauhaus modernist color variables, geometric font families, and light/dark theme classes across CSS files.
2. Web component styling invariants: Scanning 18+ Lit component source files across all microfrontends for hardcoded hex colors, raw px spacing, and missing `--rf-*` tokens.
3. WCAG contrast ratio calculations: Evaluating foreground and background color combinations across light and dark modes to enforce accessibility standards.

As Milestone 4 and 5 introduce spectator overlay themes (TASK-0056) and character leitmotif styling (TASK-0102), this test suite will expand beyond 500 lines unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Component styles and Storybook preview invariants.
- **ADR-0009: Bauhaus Modernist Design System**: Design tokens and font families.
- **ADR-0012: Dark/Light Mode Theming System**: Contrast calculation and WCAG 2.1 AA requirements.

## Product & User Story References
- **Product Requirement**: [`prd-0013-immersive-and-intuitive-frontend-experience.md`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)
- **User Story**: [`us-0041-settings-modal-and-appearance-mode-switching.md`](../../user_stories/accepted/us-0041-settings-modal-and-appearance-mode-switching.md)

## Detailed Specification & Implementation Plan
1. **Design System Tokens & Theme Definitions Suite (`tests/test_theming_tokens.py`)**:
   - Verification of `themes.css`, CSS variables, and Storybook preview theme definitions (< 150 lines).
2. **Component Token Invariants & WCAG Contrast Suite (`tests/test_theming_contrast.py`)**:
   - Static AST/regex scanning for hardcoded CSS values in microfrontend Lit components.
   - Algorithmic contrast ratio verification for WCAG AA compliance across all themes (< 170 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Modularizes test suite organization without changing design system tokens or component implementations.
- **Negotiable (N)**: Distribution of component file scans can be tuned.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and speeds up frontend token validation runs.
- **Estimable (E)**: Pure pytest partitioning using shared test helpers.
- **Small (S)**: Scope strictly isolated to `tests/test_theming.py`; all resulting files < 180 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_theming_*.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Decomposition Executed**:
   - `tests/test_theming.py` decomposed into `tests/test_theming_tokens.py` and `tests/test_theming_contrast.py`.
2. **Strict Line Limit**:
   - Both test files strictly under 200 lines in compliance with Hard Invariant 6.
3. **Full Backward Compatibility**:
   - All token and contrast assertions remain active with 100% coverage.
4. **Frontdoor Test Verification**:
   - All tests pass via `uv run pytest tests/test_theming_tokens.py tests/test_theming_contrast.py`.
