---
id: '0107'
title: Character Sheet UI Inventory Grid and Condition Indicator Microfrontend
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0009
- TASK-0018
- TASK-0077
governing_adrs:
- ADR-0003
- ADR-0004
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0006
governing_stories:
- US-0015
- US-0024
- US-0051
target_release: 0.4.0
---

# TASK-0107: Character Sheet UI Inventory Grid and Condition Indicator Microfrontend

## Status
Proposed

## Summary
Develop the Lit Web Component microfrontend `<runefoble-character-sheet>` within `services/character_sheet/ui/` to visually display character attributes, equip/unequip gear in interactive slots (`main_hand`, `off_hand`, `armor`), inspect inventory encumbrance, and display active condition pills (both 5e/d20 rules and Runefoble absence penalties).

## Problem Statement
While `services/character_sheet` provides full event-sourced backend aggregates and REST endpoints (TASK-0009, TASK-0018, PRD-0006), players lack an encapsulated, responsive microfrontend to manage equipment, track spell slots, and inspect conditions visually. Providing `<runefoble-character-sheet>` fulfills US-0015, US-0024, and US-0051.

## Governing Architecture & ADRs
- **ADR-0003**: UV Monorepo Workspace (`services/character_sheet`).
- **ADR-0004**: Lit Web Components and Storybook UI (Shadow DOM, Bauhaus design tokens).
- **ADR-0007**: API Gateway Architecture and Service Endpoints (`/api/v1/characters/...`).
- **ADR-0013**: Microfrontend Architecture and Service Component Vendoring (`services/character_sheet/ui/` exporting `/ui/manifest`).

## Scope of Work
1. **Interactive Equipment & Inventory Grid**:
   - Visual paper doll slots for `main_hand`, `off_hand`, `armor`, and accessories with drag-and-drop or click-to-equip interactions.
   - Encumbrance capacity bar color-coded by load thresholds.
2. **Condition Indicators & Absence Badges**:
   - Distinct badges for tactical conditions (`blinded`, `prone`) and absence penalties (`drunk`, `foolishness`).
3. **Spellbook & Spell Slot Tracker**:
   - Visual slot tracker with clickable pips for expenditure and recovery.
4. **Storybook & Manifest Integration**:
   - Storybook stories for normal, encumbered, and heavily conditioned character states.
   - Register component in `services/character_sheet/ui/` manifest.
5. **Frontdoor Blackbox Verification**:
   - Automated tests verifying UI manifest exposition and frontdoor interaction flows.
