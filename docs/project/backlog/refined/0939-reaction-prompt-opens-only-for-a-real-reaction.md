---
id: '0939'
title: The Reaction Prompt Opens Only for a Real Reaction
status: Refined
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0013
- ADR-0014
governing_prds: []
governing_stories:
- us-0023-spoken-reaction-interrupts-and-ready-actions
target_bc: game_session
target_release: 0.9.0
---

# TASK-0939: The Reaction Prompt Opens Only for a Real Reaction

## Status

Refined

## Summary

Every live session shows the dialog "Turn Paused: Reaction" with the text `Combatant shouted: "reaction"` and a running timer, although nobody spoke. The App Shell mounts `<runefoble-combat-reaction-prompt>` as a default `sidebar-tool` plugin, and the element is open and active by default.

## Problem Statement

- `services/game_session/ui/src/runefoble-combat-reaction-prompt.ts:20-27`: `reactingCombatantName = 'Combatant'`, `reactionType = 'reaction'`, `isOpen = true`, `status = 'active'`. `connectedCallback` starts the timer when the status is active.
- `frontend/src/components/plugins/plugin_registry.ts:101`: the element is a default plugin.
- Evidence: `.audit/work/vtt-repeat/repeat3-error-context.md` (dialog "Reaction Interrupt Prompt" in the page snapshot).

## Documentation & Architecture Review

- `docs/how-to/manage-spoken-reactions-and-ready-actions.md`, `docs/how-to/mount-community-plugin-ui-extension-slots.md`.

## Product & User Story References

- US-0023 (spoken reaction interrupts).

## Detailed Specification & Implementation Plan

1. The element is closed and idle until it receives a real reaction (a reaction id and a reacting combatant). It shows no placeholder name and starts no timer while idle.
2. Find the real source of reaction data (session frame or route). If the shell does not feed the element from it, either wire it, or remove the default plugin entry. Record the choice in the work report.
3. Update the Storybook stories so the open state is an explicit story and the default story shows the idle state.

## Frontdoor Blackbox Test Plan

- A component test: with no reaction data, the element renders no dialog and starts no timer. With reaction data, it opens.
- Orchestrator on Kind: the live session page snapshot shows no reaction dialog in the lobby and VTT scenarios.

## Definition of Done

- Tests and Storybook pass. Docs updated. CHANGELOG `Fixed` entry.

## Audit Provenance

- Severity: medium
- Source audits: .audit/work/vtt-repeat/repeat3-error-context.md
