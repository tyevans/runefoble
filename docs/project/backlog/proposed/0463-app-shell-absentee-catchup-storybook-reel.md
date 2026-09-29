---
id: '0463'
title: App Shell Absentee Catch-Up Storybook Reel Microfrontend
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0213
- TASK-0461
- TASK-0462
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0012
governing_prds:
- PRD-0002
- PRD-0012
- PRD-0023
governing_stories:
- US-0005
- US-0027
- US-0040
target_release: 0.9.0
---

# TASK-0463: App Shell Absentee Catch-Up Storybook Reel Microfrontend

## Status
Proposed

## Summary
Implement an interactive "Previously On..." storybook catch-up reel web component (`runefoble-absentee-catchup-reel`) within the App Shell. When a returning player (Sarah) logs in after missing a session where their character was controlled by an AI stand-in, present an episodic, slide-based multimedia recap summarizing key combat turns, stand-in antics, comical penalty moments ("drunk", "foolishness"), narrative revelations, and the resource audit ledger reconciliation card with Bauhaus styling and Shadow DOM encapsulation.

## Problem Statement
PRD-0002 and US-0027 Acceptance Criterion 3 require: "An interactive 'Previously On...' storybook reel summarizes key combat turns, inside jokes, and narrative revelations upon login." Currently, absent players must navigate raw chronicle logs or separate audio endpoints without visual context. There is no episodic, interactive visual storybook reel component in the frontend App Shell to welcome returning players, showcase what their character did while under AI stand-in control, and prompt them to review their resource audit before entering the live tabletop or campaign hub.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Design System & Lit Web Components**: Bauhaus modernist aesthetics with primary color accents, high contrast typography, and accessible keyboard navigation.
- **ADR-0007: Domain-Driven Design Architecture**: Presentation component consuming normalized absentee telemetry and audit ledger endpoints via Gateway API.
- **ADR-0012: Theme Mode & Color Invariants**: Compliant dark and light mode color token inheritance.

## Product & User Story References
- [`prd-0002-missing-player-ai-stand-in-with-penalties.md`](../../product/accepted/prd-0002-missing-player-ai-stand-in-with-penalties.md)
- [`us-0005-absentee-session-chronicle-recap.md`](../../user_stories/accepted/us-0005-absentee-session-chronicle-recap.md)
- [`us-0027-absentee-character-resource-ledger-and-recap-reel.md`](../../user_stories/accepted/us-0027-absentee-character-resource-ledger-and-recap-reel.md)

## Scope of Work
1. **Lit Web Component (`frontend/src/components/runefoble-absentee-catchup-reel.ts`)**:
   - Implement `runefoble-absentee-catchup-reel` with episodic slide carousel:
     - Slide 1 (Welcome & Absence Summary): Duration missed, active penalty ("drunk", "foolishness"), standing in party.
     - Slide 2 (Key Combat Highlights): Critical hits/fumbles, clutch saves, tactical damage dealt/taken with spatial badges.
     - Slide 3 (Narrative & Social Antics): Comedic stand-in dialogue quotes, inside jokes, major faction/plot developments.
     - Slide 4 (Resource Audit & Reconciliation Card): Itemized spell slots, potions consumed, DM reconciliation status badge, and "Dismiss & Enter Tabletop" button.
2. **Keyboard & Carousel Navigation (`frontend/src/components/absentee_reel/navigation.ts`)**:
   - Left/Right arrow keys, swipe gestures, progress bar indicators, and skip button.
3. **Storybook Stories (`frontend/src/stories/absentee-catchup-reel.stories.ts`)**:
   - Scenarios: `DefaultReel`, `DrunkAfflictionHighlights`, `ClutchSurvivalReel`, `FullyReconciledLedger`, `DarkModeTheme`.
4. **App Shell Route Hook (`frontend/src/shell/absentee_prompt.ts`)**:
   - Prompt returning players with a modal overlay if unviewed absentee reels exist when navigating to `#/campaigns/:id`.

## Definition of Done
1. `runefoble-absentee-catchup-reel.ts` and modular helper files stay strictly < 250 lines each per Hard Invariant 6.
2. Component adheres to Shadow DOM encapsulation and inherits Bauhaus CSS custom properties.
3. Interactive Storybook stories render without console warnings or layout regressions.
4. Unit tests in `frontend/test/` assert slide transitions, keyboard controls, and dismiss events.
