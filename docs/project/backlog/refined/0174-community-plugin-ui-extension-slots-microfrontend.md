---
id: '0174'
title: Community Plugin UI Extension Slots Microfrontend
status: Refined
created: 2026-09-26
dependencies:
- TASK-0057
- TASK-0172
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0022
governing_stories:
- US-0035
target_release: 0.7.0
---

# TASK-0174: Community Plugin UI Extension Slots Microfrontend

## Status
Refined

## Summary
Implement extensible mounting slots and Shadow DOM sandboxing in the frontend design system (`frontend/src/components/plugins/`), allowing community-authored Lit Web Components to mount into designated extension slots (such as `hud-widget`, `dice-panel`, and `sidebar-tool`) with full Bauhaus theme token inheritance and secure event isolation.

## Problem Statement
Community modders currently have no standardized, secure UI extension slots to embed custom dice rollers, soundboards, or inventory calculators without patching core frontend templates. Without formal extension slot encapsulation, third-party styles leak into the App Shell and DOM mutators risk breaking core gameplay synchronizations.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Encapsulated Web Components with Shadow DOM isolation and Storybook verification.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: Bauhaus CSS custom properties inheritance into sandboxed slots.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Modular component packaging under 200 lines per module.

## Product & User Story References
- **Product Requirement**: [`prd-0022-extensible-modder-platform-and-mcp-registry.md`](../../product/accepted/prd-0022-extensible-modder-platform-and-mcp-registry.md)
- **User Story**: [`us-0035-runtime-mcp-tool-hot-reloading-and-extension-slots.md`](../../user_stories/accepted/us-0035-runtime-mcp-tool-hot-reloading-and-extension-slots.md)

## Detailed Specification & Implementation Plan
1. **Extension Slot Container (`frontend/src/components/plugins/runefoble-plugin-slot.ts`)**:
   - Custom element `<runefoble-plugin-slot>` accepting slot identifiers (`hud-widget`, `dice-panel`, `sidebar-tool`) and rendering slotted fallback placeholders (< 140 lines).
2. **Plugin Registration & Lifecycle Manager (`frontend/src/components/plugins/plugin_registry.ts`)**:
   - Registry allowing dynamic registration, unregistration, and query of custom element tags associated with slot targets (< 120 lines).
3. **Shadow DOM Sandbox & CSS Custom Property Bridge (`frontend/src/components/plugins/plugin_sandbox.ts`)**:
   - Boundary ensuring third-party CSS rules cannot escape slot boundaries while allowing `--rf-color-*` and `--rf-space-*` design tokens to pierce (< 110 lines).
4. **Storybook Interactive Demonstration (`frontend/src/stories/runefoble-plugin-slot.stories.ts`)**:
   - Storybook stories demonstrating mock third-party widgets mounted in sidebar, header, and dice tray slots under Dark and Light themes (< 130 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Consumes completed TASK-0172 MCP tool registry and frontend slot contracts without altering core session state aggregates.
- **Negotiable (N)**: Slot layout positions, alignment flex directions, and fallback placeholder views are configurable.
- **Valuable (V)**: Empowers community creators to extend the VTT UI with custom tools while maintaining visual coherence and platform security.
- **Estimable (E)**: Pure Lit Web Component slotting and DOM lifecycle management.
- **Small (S)**: Bounded strictly to `frontend/src/components/plugins/`; all files strictly < 150 lines.
- **Testable (T)**: Frontdoor blackbox tests verify custom element mounting, attribute reactivity, and theme token inheritance.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Microfrontend Architecture**:
   - Extension slot `<runefoble-plugin-slot>` implemented with Shadow DOM encapsulation.
   - All modules in `frontend/src/components/plugins/` strictly < 150 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_plugin_slots/` verifies component registration, mounting, event bubbling, and unmount cleanup.
3. **Quality Gates**:
   - Storybook stories render and verify cleanly.
   - Passes `uv run pytest tests/test_blackbox_plugin_slots/`, `uv run ruff check .`, and `uv run ruff format --check .`.
