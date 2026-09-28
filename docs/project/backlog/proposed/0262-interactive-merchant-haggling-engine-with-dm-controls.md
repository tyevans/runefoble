---
id: '0262'
title: Interactive Merchant Haggling Engine with DM Arbitration Controls
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0260
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0004
governing_prds:
- PRD-0024
governing_stories:
- US-0075
target_release: 0.8.0
---

# TASK-0262: Interactive Merchant Haggling Engine with DM Arbitration Controls

## Status
Proposed

## Summary
Implement a dynamic merchant bartering and haggling engine with a tug-of-war price meter, persuasive dialogue moves, merchant patience/temperament meters, and real-time DM arbitration controls for nudging moods, injecting custom dialogue barks, or overriding transaction terms.

## Problem Statement
Buying weapons, armor, bread, or potions in virtual tabletops is typically a static spreadsheet transaction. There is no participatory haggling minigame that balances player roleplay and charisma checks with merchant personalities, nor can the Game Master intervene in real time without halting the interface.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/run-tavern-minigames-and-merchant-haggling.md`: Personality-driven merchant bartering.
  - `docs/how-to/manage-dm-copilot-whispers-and-veto-overrides.md`: Human DM veto and narrative copilot overrides.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: DM role enforcement for transaction overrides.
  - **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Intent evaluation and dialogue synthesis.
  - **ADR-0004: Lit Web Components and Storybook UI**: Interactive negotiation drawer component.

## Product & User Story References
- **Product Requirement**: [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
- **User Story**: [`us-0075-dynamic-merchant-haggling-with-dm-arbitration.md`](../../user_stories/accepted/us-0075-dynamic-merchant-haggling-with-dm-arbitration.md)

## Detailed Specification & Implementation Plan
1. **Domain Logic & Valuation Rules (`services/game_session/haggling/`)**:
   - `NegotiationSession`: Tracks original price, current offer, merchant base margin, patience points (1-5), and temperament modifiers (e.g. Greedy, Stubborn, Vain, Generous).
   - Bargaining Gambits: "Flattery / Praise", "Bulk Order Promise", "Point Out Flaw", "Hard Intimidation", "Walk Away Bluff".
   - Persuasion/Intimidation roll evaluation against merchant DC.
2. **DM Real-Time Control Panel (`frontend/src/components/dm-controls/`)**:
   - Live negotiation drawer allowing the DM to see current offers and merchant patience.
   - One-click mood modifiers: "Soothe Merchant", "Enrage Merchant", "Accept Deal", "Refuse & Kick Out".
   - Custom in-character bark injection field broadcasted via WebSockets.
3. **Frontend Component (`runefoble-merchant-haggler.ts`)**:
   - Responsive touch UI with sliding price scale, active dialogue cards, and merchant portrait emotion reaction.

## Definition of Done
- Bartering transactions deduct and credit player currency cleanly through domain events.
- DM override immediately terminates or completes the exchange with zero race conditions.
- Test coverage validates gambit mechanics and boundary conditions.
- All files strictly under 400 lines.
