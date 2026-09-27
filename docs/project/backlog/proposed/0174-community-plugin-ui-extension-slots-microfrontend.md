---
id: '0174'
title: Community Plugin UI Extension Slots Microfrontend
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0057
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
Proposed

## Summary
Implement extensible mounting slots and Shadow DOM sandboxing in `frontend/` allowing community-authored Lit Web Components to mount into sidebar, header, and character sheet tabs.

## Problem Statement
Community modders currently have no standardized, secure UI extension slots to embed custom dice rollers, soundboards, or inventory calculators without patching core frontend templates.

## Governing Architecture & ADRs
- **ADR-0004: Lit + Vite Microfrontends with Storybook**: Plugin mounting architecture.
- **ADR-0012: CSS Custom Properties & Semantic Dark/Light Invariants**: Theme token inheritance.
- **ADR-0013: Modular Microfrontend Decomposition**: Component subviews < 200 lines.

## Scope of Work
1. **Extension Slot Mount Container**:
   - `plugin-extension-slot` Lit component managing registration and lifecycle of custom DOM nodes.
2. **Shadow DOM Sandbox & Event Bridge**:
   - Sandboxing boundary ensuring plugin styles do not pollute global CSS variables.
3. **Frontdoor Verification**:
   - Storybook stories demonstrating mock third-party widgets mounted in sidebar and header slots.

## Definition of Done
- Extension slot component implemented in `frontend/src/components/plugins/`.
- Theme tokens propagate into sandboxed custom elements cleanly.
- Tests verify component mounting and unmounting without memory leaks.
- Component stays under 200 lines.
