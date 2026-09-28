---
id: '0288'
title: Frontend Character Management Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0258
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0064
- US-0069
target_release: 0.8.0
---

# TASK-0288: Frontend Character Management Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `frontend/test/character-management-and-profile.test.ts` (331 lines, 66.2% of limit) into modular TypeScript test submodules under `frontend/test/character_management/` (`creation.test.ts`, `roster-binding.test.ts`, `profile-settings.test.ts`), ensuring all test modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`frontend/test/character-management-and-profile.test.ts` handles character creation modal events, character roster binding, staging lobby character selection, dynamic VTT card binding, profile settings view rendering, and campaign deduplication assertions in a single 331-line suite. As character sheets support multiclassing and advanced equipment interactions, this frontend test suite will approach the 500-line invariant limit unless modularized.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Character card custom element encapsulation and test contracts.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast character token styling and badges.
- **ADR-0013: Frontend Microfrontend Architecture**: Decoupled character roster and pre-game lobby components.

## Scope of Work
1. **Character Creation Modal Tests (`frontend/test/character_management/creation.test.ts`)**:
   - Extract character creation modal rendering, form field input validation, and submission event dispatching (< 110 lines).
2. **Character Roster & Lobby Binding Tests (`frontend/test/character_management/roster-binding.test.ts`)**:
   - Extract campaign roster rendering, active character selection in staging lobby, dynamic VTT card binding, and avatar sync (< 120 lines).
3. **Profile Settings & Campaign Deduplication Tests (`frontend/test/character_management/profile-settings.test.ts`)**:
   - Extract profile settings view rendering, campaign creation form idempotency, and duplicate submission prevention (< 110 lines).
4. **Verification**:
   - Safely remove monolithic `frontend/test/character-management-and-profile.test.ts` and ensure `npm test` runs all submodules with 100% passing rate.

## Definition of Done
- `frontend/test/character-management-and-profile.test.ts` decomposed into `frontend/test/character_management/` suite.
- All extracted test modules strictly < 130 lines per Hard Invariant 6.
- 100% test passing via `npm test` in `frontend/`.
- Monolithic `frontend/test/character-management-and-profile.test.ts` safely removed.
