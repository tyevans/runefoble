---
id: '0158'
title: Reactive Combat Reactions & Interrupt Prompt Microfrontend
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0155
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0001
governing_stories:
- US-0023
target_release: 0.6.0
---

# TASK-0158: Reactive Combat Reactions & Interrupt Prompt Microfrontend

## Status
Proposed

## Summary
Build `<runefoble-combat-reaction-prompt>` Web Component in `services/game_session/ui/src/` to display interactive reaction interrupt prompts, ready-action confirmation toasts, and countdown resolution bars during paused combat turns.

## Problem Statement
When combat is paused by a spoken reaction (TASK-0155) or when a ready-action trigger fires, players need immediate, tactile UI prompts to select reaction options ("Cast Shield [-1 slot]", "Opportunity Attack", "Decline") before turn timeout expires.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Lit Web Component with Shadow DOM.
- **ADR-0012: Theming System and Accessibility Contrast Invariants**: Accessible countdown timers and high-contrast action buttons.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Vendored inside `services/game_session/ui/`.

## Scope of Work
1. **Reaction Prompt Dialog**:
   - Urgent modal overlay displaying triggered condition, eligible reactions, and time-remaining progress bar (< 150 lines).
2. **Ready-Action Creator Card**:
   - UI panel for defining custom trigger condition phrases and assigned action (< 130 lines).
3. **Storybook Stories**:
   - Stories showing active prompt countdown, trigger accepted, and timeout dismissed states.
4. **Manifest Export**:
   - Register custom element in `services/game_session/` UI manifest.
