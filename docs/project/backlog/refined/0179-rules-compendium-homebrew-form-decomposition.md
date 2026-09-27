---
id: '0179'
title: Rules Compendium Homebrew Subview Modular Decomposition
status: Refined
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0004
- ADR-0013
governing_prds:
- PRD-0008
governing_stories:
- US-0037
- US-0052
target_release: 0.7.0
---

# TASK-0179: Rules Compendium Homebrew Subview Modular Decomposition

## Status
Refined

## Summary
Decompose `services/rules_compendium/ui/src/runefoble-rules-compendium.ts` (374 lines, 74.8% of limit) by extracting the inline homebrew creation form, validation logic, and custom monster/spell state into a dedicated Web Component subview `runefoble-homebrew-creator.ts`, keeping all compendium UI components strictly < 200 lines per Hard Invariant 6 and ADR-0013.

## Problem Statement
`services/rules_compendium/ui/src/runefoble-rules-compendium.ts` serves as the root shell microfrontend for the rules compendium. While the search lookup and encounter builder tabs are delegated to subcomponents (`runefoble-rules-lookup.ts` and `runefoble-encounter-builder.ts`), the homebrew creation form and its corresponding form state and validation handlers remain directly embedded within the parent component. This has caused `runefoble-rules-compendium.ts` to expand to 374 lines.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular package structure across bounded contexts.
- **ADR-0004: Bauhaus Design System**: Consistent typography, design tokens, and modular UI hierarchy.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Decomposed, single-responsibility Web Components with Shadow DOM encapsulation.

## Detailed Specification & Implementation Plan
1. **Homebrew Subview Component (`services/rules_compendium/ui/src/runefoble-homebrew-creator.ts`)**:
   - Extract homebrew draft properties, form inputs, validation checks, and submission handling into `<runefoble-homebrew-creator>` (< 180 lines).
   - Dispatch custom event `homebrew-created` upon successful submission.
2. **Parent Compendium Shell Refactoring (`services/rules_compendium/ui/src/runefoble-rules-compendium.ts`)**:
   - Import `<runefoble-homebrew-creator>` and delegate the `'homebrew'` tab rendering to the new subview (< 160 lines).
3. **Storybook Stories & Manifest**:
   - Ensure the new subcomponent is properly documented and verified in Storybook.
   - Verify `/ui/manifest` continues to expose required custom elements cleanly.
4. **Verification**:
   - Run blackbox tests in `tests/test_blackbox_rules_compendium_ui.py` and TypeScript build checks.

## INVEST Criteria Evaluation
- **Independent (I)**: Frontend subview extraction without changes to backend REST endpoints.
- **Negotiable (N)**: Form field grouping and validation error rendering can follow standard Bauhaus layout patterns.
- **Valuable (V)**: Protects `runefoble-rules-compendium.ts` from breaching Hard Invariant 6 (500 lines) and improves UI maintainability.
- **Estimable (E)**: Standard Lit component extraction and event dispatching.
- **Small (S)**: Bounded strictly to `services/rules_compendium/ui/src/`; all components < 200 lines.
- **Testable (T)**: Frontdoor verification via Storybook and `tests/test_blackbox_rules_compendium_ui.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `runefoble-rules-compendium.ts` reduced to < 180 lines.
   - `runefoble-homebrew-creator.ts` created and strictly < 200 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - All Storybook stories render without console errors.
   - `tests/test_blackbox_rules_compendium_ui.py` passes cleanly.
3. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_rules_compendium_ui.py`, `uv run ruff check .`, and `uv run ruff format --check .`.
