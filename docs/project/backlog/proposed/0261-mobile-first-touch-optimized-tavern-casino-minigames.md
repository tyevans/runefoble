---
id: '0261'
title: Mobile-First Touch-Optimized Tavern and Casino Minigames Suite
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0259
- TASK-0170
governing_adrs:
- ADR-0004
- ADR-0006
- ADR-0012
governing_prds:
- PRD-0024
governing_stories:
- US-0074
target_release: 0.8.0
---

# TASK-0261: Mobile-First Touch-Optimized Tavern and Casino Minigames Suite

## Status
Proposed

## Summary
Develop a suite of responsive, touch-first Lit Web Components and WebSocket multiplayer engines for tavern and casino minigames—including Darts, Pool/Billiards, Liar's Dice, Roulette, and Dragon Craps—optimized specifically for mobile smartphone browsers without requiring native app installation.

## Problem Statement
Tabletop downtime minigames currently either exist as desktop-only components or lack touch kinematics, haptic integration, and multiplayer turn synchronization. Players resting at tavern or casino establishments cannot pull out their phones to casually play darts or bet copper with friends at the table.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/run-tavern-minigames-and-merchant-haggling.md`: Liar's Dice and tavern wagering.
  - `docs/how-to/simulate-tabletop-3d-physics-and-collisions.md`: 3D dice physics and tray collisions.
  - `docs/how-to/connect-mobile-companion-and-haptic-gateway.md`: Mobile touch and haptic feedback.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Encapsulated canvas and Web Component controls.
  - **ADR-0006: Redis Streams Event Streaming**: Real-time multiplayer synchronization.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast geometric gaming tables.

## Product & User Story References
- **Product Requirement**: [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
- **User Story**: [`us-0074-interactive-mobile-tavern-and-casino-minigames.md`](../../user_stories/accepted/us-0074-interactive-mobile-tavern-and-casino-minigames.md)

## Detailed Specification & Implementation Plan
1. **Frontend Touch Components (`frontend/src/components/minigames/`)**:
   - `runefoble-minigame-darts.ts`: 2D canvas with flick velocity, trajectory calculation, and cricket/501 rules.
   - `runefoble-minigame-pool.ts`: Overhead 2D billiards canvas with cue angle control, touch pull-back power, and ball collision physics.
   - `runefoble-minigame-liars-dice.ts`: Accelerometer/swipe cup shaker, private peek shade, bluff bids, and elimination tracker.
   - `runefoble-minigame-roulette.ts`: Felt wagering table layout, rotating wheel animation, and multiplayer bet tokens.
   - `runefoble-minigame-craps.ts`: Two-finger dice toss onto felt tray with pass line and proposition bets.
2. **Haptic & Audio Polish**:
   - Native browser haptic pulses via `navigator.vibrate([15, 30, 15])` upon dice collision, dart impact, or cup shake.
   - Audio foley cues for felt rolling, wooden clatter, and crowd reactions.
3. **Real-Time Multiplayer Synchronization**:
   - WebSocket router dispatching game moves, bets, and dice results across all players joined to the establishment's table channel.

## Definition of Done
- All minigames run smoothly on 375px-wide mobile viewports at 60 FPS.
- Multiplayer turn state and bet payouts synchronize across connected clients in <150ms.
- Components verified in Storybook across dark and light Bauhaus themes.
- Files remain strictly under 400 lines.
