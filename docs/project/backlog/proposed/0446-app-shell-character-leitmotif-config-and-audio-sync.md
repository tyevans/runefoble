---
id: '0446'
title: App Shell Character Leitmotif Configuration & Audition Integration
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0102
- TASK-0255
- TASK-0436
governing_adrs:
- ADR-0002
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0010
- PRD-0016
- PRD-0023
governing_stories:
- US-0039
- US-0046
- US-0069
target_release: 0.9.0
---

# TASK-0446: App Shell Character Leitmotif Configuration & Audition Integration

## Status
Proposed

## Summary
Mount the `<runefoble-leitmotif-config>` component within the App Shell character sheet view (`frontend/src/runefoble-app.ts`), integrate leitmotif profile management into `frontend/src/services/app-data-service.ts`, handle `@leitmotif-configured` and `@leitmotif-audition` events by calling Gateway Soundscape endpoints, and play back audition audio stings via the frontend WebAudio pipeline.

## Problem Statement
The `<runefoble-leitmotif-config>` component exists in `@runefoble/soundscape-controls`, allowing players to select musical instruments (heroic brass, haunting flute, somber cello, arcane synthesizer) and audition dynamic stinger motifs. However, the component is not mounted in the App Shell character sheet route (`#/characters/:id`). As a result, players have no UI mechanism to personalize their character's musical leitmotif signature or audition how their theme sounds during critical moments. Furthermore, `AppDataService` has no client methods for querying or updating character leitmotif profiles.

## Governing Architecture & ADRs
- **ADR-0002: Real-Time Audio Pipeline and WebAudio Ducking**: Auditioning stinger audio via WebAudio without interrupting voice streaming.
- **ADR-0004: Lit Web Components and Storybook UI**: Lit Shadow DOM component encapsulation and custom event handling.
- **ADR-0013: Frontend Microfrontend Architecture**: Microfrontend composition within the centralized App Shell.

## Product & User Story References
- [`prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md`](../../product/accepted/prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md)
- [`prd-0010-adaptive-soundscape-foley-and-tension-scoring.md`](../../product/accepted/prd-0010-adaptive-soundscape-foley-and-tension-scoring.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0046-character-musical-leitmotifs-and-dynamic-themes.md`](../../user_stories/accepted/us-0046-character-musical-leitmotifs-and-dynamic-themes.md)
- [`us-0039-adaptive-tension-and-combat-audio-scoring.md`](../../user_stories/accepted/us-0039-adaptive-tension-and-combat-audio-scoring.md)

## Scope of Work
1. **App Data Service Leitmotif Client (`frontend/src/services/app-data-service.ts`)**:
   - Add `fetchCharacterLeitmotif(characterId: string): Promise<LeitmotifProfile>` (< 30 lines).
   - Add `updateCharacterLeitmotif(characterId: string, profile: Partial<LeitmotifProfile>): Promise<LeitmotifProfile>` (< 30 lines).
   - Add `auditionCharacterLeitmotif(characterId: string, timbre: string): Promise<{ audioUrl?: string }>` (< 30 lines).
   - Add fallback mock data for offline development.
2. **App Shell Character Sheet Integration (`frontend/src/runefoble-app.ts`)**:
   - Import `<runefoble-leitmotif-config>` and render within the character sheet view layout (< 40 lines).
   - Bind `@leitmotif-configured` event: call `appDataService.updateCharacterLeitmotif()` and display toast confirmation.
   - Bind `@leitmotif-audition` event: trigger audio stinger audition through `webaudio-pipeline.ts`.
3. **Verification**:
   - Author frontend tests asserting component rendering, property reflection, and event dispatch upon timbre selection and save actions.

## Definition of Done
1. `<runefoble-leitmotif-config>` mounted and functional in the character sheet route.
2. Players can select instrument signatures, audition themes, and save their character's musical leitmotif.
3. Audio stings audition cleanly via WebAudio pipeline without blocking voice channels.
4. All unit and component tests pass (`npm test`).
5. All touched files adhere to Hard Invariant 6 (< 500 lines).
