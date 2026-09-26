---
id: '0108'
title: Rules Compendium Search & Encounter Builder Microfrontend
status: Refined
created: 2026-09-26
dependencies:
- TASK-0048
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0004
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0008
governing_stories:
- US-0034
- US-0037
- US-0052
target_release: 0.4.0
---

# TASK-0108: Rules Compendium Search & Encounter Builder Microfrontend

## Status
Refined

## Summary
Develop the encapsulated Lit Web Component microfrontend `<runefoble-rules-compendium>` within `services/rules_compendium/ui/` providing sub-50ms hybrid BM25 and vector search across SRD monsters, spells, and conditions, alongside an interactive CR encounter builder interface.

## Problem Statement
`services/rules_compendium` implements backend aggregates and redstring hybrid retrieval (TASK-0048, PRD-0008). Dungeon Masters (Evelyn) and players need an in-session floating drawer or split view to query rules instantly without leaving the game board, fulfilling US-0034, US-0037, and US-0052.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Zanzibar campaign scoping for custom homebrew rules (`campaign:xyz#view_homebrew`).
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Scaffolding UI in `services/rules_compendium/ui/`.
- **ADR-0004: Lit Web Components and Storybook UI**: Shadow DOM encapsulation with Bauhaus geometric design tokens.
- **ADR-0007: API Gateway Architecture and Service Endpoints**: Unified API Gateway routing for compendium queries (`/api/v1/compendium/...`).
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Service-vendored UI package serving `/ui/manifest`.

## Product & User Story References
- **Product Requirement**: [`prd-0008-ttrpg-rules-compendium-and-encounter-builder.md`](../../product/accepted/prd-0008-ttrpg-rules-compendium-and-encounter-builder.md)
- **User Stories**:
  - [`us-0034-agnostic-ttrpg-ruleset-schemas-and-system-expansion.md`](../../user_stories/accepted/us-0034-agnostic-ttrpg-ruleset-schemas-and-system-expansion.md)
  - [`us-0037-automated-cr-encounter-balancing-and-compendium.md`](../../user_stories/accepted/us-0037-automated-cr-encounter-balancing-and-compendium.md)
  - [`us-0052-homebrew-spell-monster-and-rule-authoring.md`](../../user_stories/accepted/us-0052-homebrew-spell-monster-and-rule-authoring.md)

## Detailed Specification & Implementation Plan
1. **Instant Search Input with Debounced Autocomplete**:
   - Sub-50ms query latency querying compendium hybrid search endpoint.
   - Filter pills for Spells, Monsters, Conditions, and Homebrew.
2. **Interactive CR Encounter Builder Panel**:
   - Party level / size sliders dynamically computing XP thresholds (Easy, Medium, Hard, Deadly).
   - Monster card drag-and-drop adding creatures to encounter draft with real-time lethality calculation.
3. **Homebrew Creation Modal**:
   - Form-based creature and spell creator validating against compendium JSON schemas.
4. **Storybook Stories & Manifest**:
   - Interactive Storybook coverage with sample monster stat blocks and encounter balance states.
   - Manifest registration in `services/rules_compendium/ui/` with `/ui/manifest` exposition.

## INVEST Criteria Evaluation
- **Independent (I)**: Standalone microfrontend querying existing compendium service endpoints.
- **Negotiable (N)**: Layout of search results drawer vs popup inspector can be customized.
- **Valuable (V)**: Eliminates session interruptions from manual rulebook leafing.
- **Estimable (E)**: Follows established microfrontend and Lit component standards.
- **Small (S)**: Scope strictly isolated to `services/rules_compendium/ui/`; all files < 200 lines.
- **Testable (T)**: Frontdoor blackbox test suite asserting component registration, search queries, and encounter balance updates.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Microfrontend Element**:
   - `<runefoble-rules-compendium>` component rendered with complete Shadow DOM encapsulation and Bauhaus tokens.
2. **Storybook Stories**:
   - Stories for search results, monster stat cards, and CR encounter balance calculator with zero console errors.
3. **Microfrontend Manifest**:
   - Manifest served at `/ui/manifest` exposing tags, styles, and script entries per ADR-0013.
4. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_rules_compendium_ui.py` validating component registration, manifest endpoint, and REST data binding.
5. **Quality Gates**:
   - Strictly conforms to Hard Invariant 6 (< 500 lines per file).
   - Passes `pnpm run build` and `uv run pytest tests/test_blackbox_rules_compendium_ui.py`.
