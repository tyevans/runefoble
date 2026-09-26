---
id: '0101'
title: Generative Diegetic Handouts, Wax Seals & 3D Relic Inspector
status: Refined
created: 2026-09-26
dependencies:
- TASK-0023
- TASK-0047
- TASK-0049
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0010
- ADR-0013
target_release: 0.4.0
governing_prds:
- PRD-0015
governing_stories:
- US-0045
---

# TASK-0101: Generative Diegetic Handouts, Wax Seals & 3D Relic Inspector

## Status
Refined

## Summary
Build an in-world diegetic artifact generation pipeline and interactive WebGL relic inspector, providing weathered letters with breakable wax seals, hidden runes, and rotating 3D magical items.

## Problem Statement
Finding fantasy clues or magical artifacts is currently limited to plain text modals or flat static PNG images (PRD-0015, US-0045). Chroniclers and players like Rowan need tactile artifacts they can interact with, unseal with sound effects, and rotate in 3D to inspect hidden inscriptions and runes.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Domain logic in `services/campaign_lore` and `services/asset_forge`.
- **ADR-0006: Redis Streams Event Bus**: Event streaming for `HandoutGenerated`, `WaxSealBroken`, and `RelicInspected`.
- **ADR-0010: OpenTelemetry Distributed Tracing & Metrics**: Pipeline instrumentation.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Lit Web Components `<runefoble-handout-viewer>` and `<runefoble-relic-inspector>` in `services/campaign_lore/ui/src/`.

## Product & User Story References
- **Product Requirement**: [`prd-0015-generative-handouts-relic-inspector-and-printable-forge.md`](../../product/accepted/prd-0015-generative-handouts-relic-inspector-and-printable-forge.md)
- **User Story**: [`us-0045-generative-in-world-handouts-and-relic-inspector.md`](../../user_stories/accepted/us-0045-generative-in-world-handouts-and-relic-inspector.md)

## Detailed Specification & Implementation Plan
1. **Generative Diegetic Handout Engine (`services/campaign_lore/src/campaign_lore/handouts.py`)**:
   - Synthesizer generating weathered parchment textures, stylized calligraphy, and wax seal graphics.
   - UV-reactive invisible ink layer revealed under simulated torchlight cursor.
2. **Breakable Wax Seal Physics & Audio**:
   - Dynamic stamp cracking animation and synthesized audio acoustic feedback upon interaction.
3. **Interactive 3D WebGL Relic Inspector**:
   - WebGL canvas component with orbit controls, metallic shaders, and clickable rune hitboxes.
4. **Microfrontend Components & Storybook (`services/campaign_lore/ui/src/`)**:
   - Vendored Lit Web Components `<runefoble-handout-viewer>` and `<runefoble-relic-inspector>` with `/ui/manifest` discovery.
5. **Frontdoor Blackbox Verification**:
   - Blackbox test suite verifying artifact generation, seal states, and 3D asset metadata.

## INVEST Criteria Evaluation
- **Independent (I)**: Builds on asset forge and campaign lore pipelines without modifying underlying battlemap generation.
- **Negotiable (N)**: 3D model geometry primitives vs procedural procedural meshes.
- **Valuable (V)**: Delivers tactile, physical-feeling mystery and loot discovery to players.
- **Estimable (E)**: Scoped cleanly across Python asset generator and Lit UI components.
- **Small (S)**: Decomposed into focused modules under 200 lines each.
- **Testable (T)**: Validated end-to-end via frontdoor REST routes and blackbox tests.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Microfrontend Vendoring**:
   - `<runefoble-handout-viewer>` and `<runefoble-relic-inspector>` built and vendored in `services/campaign_lore/ui/` with `/ui/manifest`.
2. **Strict Line Limit**:
   - All created files strictly under 300 lines in compliance with Hard Invariant 6 (< 500 lines).
3. **Frontdoor Test Verification**:
   - All scenarios verified through public HTTP routes and published CloudEvents (`HandoutGenerated`, `WaxSealBroken`, `RelicInspected`).
4. **Documentation Integrity**:
   - Diataxis how-to guide authored and documented in `docs/how-to/`.
