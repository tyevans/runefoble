---
id: '0261'
title: Mobile-First Touch-Optimized Tavern and Casino Minigames Suite
status: Complete
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
pr_url: https://github.com/tyevans/runefoble/pull/323
---
# TASK-0261: Mobile-First Touch-Optimized Tavern and Casino Minigames Suite

## Status
Refined

## Summary
Develop a suite of responsive, touch-first Lit Web Components and WebSocket multiplayer engines for tavern and casino minigames—including Darts, Pool/Billiards, Liar's Dice, Roulette, and Dragon Craps—optimized specifically for mobile smartphone browsers without requiring native app installation.

## Problem Statement
Tabletop downtime minigames currently either exist as desktop-only components or lack touch kinematics, haptic integration, and multiplayer turn synchronization. Players resting at tavern or casino establishments cannot pull out their phones to casually play darts or bet copper with friends at the table.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/run-tavern-minigames-and-merchant-haggling.md`: Liar's Dice and tavern wagering.
  - `docs/how-to/simulate-tabletop-3d-physics-and-collisions.md`: 3D dice physics and tray collisions.
  - `docs/how-to/connect-mobile-companion-and-haptic-gateway.md`: Mobile touch and haptic feedback.
  - `docs/how-to/develop-lit-components-in-storybook.md`: Touch event handling and responsive sizing in Lit.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Encapsulated canvas and Web Component controls.
  - **ADR-0006: Redis Streams Event Streaming**: Real-time multiplayer game event synchronization over WebSockets.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast geometric gaming tables and tokens.

## Product & User Story References
- **Product Requirement**: [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
- **User Story**: [`us-0074-interactive-mobile-tavern-and-casino-minigames.md`](../../user_stories/accepted/us-0074-interactive-mobile-tavern-and-casino-minigames.md)

## Detailed Specification & Implementation Plan
1. **Frontend Touch Components (`frontend/src/components/minigames/`)**:
   - `runefoble-minigame-darts.ts`: 2D canvas with flick velocity, trajectory calculation, and cricket/501 rules (< 300 lines).
   - `runefoble-minigame-liars-dice.ts`: Accelerometer/swipe cup shaker, private peek shade, bluff bids, and elimination tracker (< 280 lines).
   - `runefoble-minigame-roulette.ts`: Felt wagering table layout, rotating wheel animation, and multiplayer bet tokens (< 280 lines).
2. **Haptic & Audio Polish**:
   - Native browser haptic pulses via `navigator.vibrate([15, 30, 15])` upon dice collision, dart impact, or cup shake.
   - Audio foley cues for felt rolling, wooden clatter, and crowd reactions.
3. **Real-Time Multiplayer Synchronization**:
   - WebSocket router dispatching game moves, bets, and dice results across all players joined to the establishment's table channel.
4. **Frontdoor Blackbox Verification (`tests/test_blackbox_minigames_suite.py`)**:
   - Verify WebSocket table joining, bet placement, dice roll turn transition, and payout calculation.

## INVEST Criteria Evaluation
- **Independent (I)**: Minigame components mount into establishment modal or standalone mobile view.
- **Negotiable (N)**: Individual minigame visual styling and rules variations can be adjusted.
- **Valuable (V)**: Enables instant casual multiplayer tabletop downtime engagement on mobile devices.
- **Estimable (E)**: Component architecture and touch physics sized within a single development pass.
- **Small (S)**: Each minigame encapsulated in a focused component strictly < 300 lines.
- **Testable (T)**: Frontdoor DOM and WebSocket message assertions verify game loop execution.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. All minigames run smoothly on 375px-wide mobile viewports at 60 FPS.
2. Multiplayer turn state and bet payouts synchronize across connected clients in <150ms via WebSockets.
3. Components verified in Storybook across dark and light Bauhaus themes.
4. Blackbox frontdoor tests pass via `uv run pytest tests/test_blackbox_minigames_suite.py`.
5. All files remain strictly under 400 lines per `AGENTS.md` Rule 6.
