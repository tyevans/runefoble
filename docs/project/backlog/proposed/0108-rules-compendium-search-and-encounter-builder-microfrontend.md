---
id: '0108'
title: Rules Compendium Search & Encounter Builder Microfrontend
status: Proposed
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
Proposed

## Summary
Develop the encapsulated Lit Web Component microfrontend `<runefoble-rules-compendium>` within `services/rules_compendium/ui/` providing sub-50ms hybrid BM25 and vector search across SRD monsters, spells, and conditions, alongside an interactive CR encounter builder interface.

## Problem Statement
`services/rules_compendium` implements backend aggregates and redstring hybrid retrieval (TASK-0048, PRD-0008). Dungeon Masters (Evelyn) and players need an in-session floating drawer or split view to query rules instantly without leaving the game board, fulfilling US-0034, US-0037, and US-0052.

## Governing Architecture & ADRs
- **ADR-0001**: SpiceDB Zanzibar Object Authorization (Zanzibar campaign scoping for custom homebrew rules).
- **ADR-0003**: UV Monorepo Workspace (`services/rules_compendium`).
- **ADR-0004**: Lit Web Components and Storybook UI (Shadow DOM encapsulation, Bauhaus tokens).
- **ADR-0007**: Unified API Gateway (`/api/v1/compendium/...`).
- **ADR-0013**: Microfrontend Architecture and Service Component Vendoring (`services/rules_compendium/ui/`).

## Scope of Work
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
5. **Frontdoor Verification**:
   - End-to-end blackbox tests for HTTP frontdoors and UI component manifests.
