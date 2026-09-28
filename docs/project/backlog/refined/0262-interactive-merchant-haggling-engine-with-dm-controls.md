---
id: '0262'
title: Interactive Merchant Haggling Engine with DM Arbitration Controls
status: Refined
created: 2026-09-27
dependencies:
- TASK-0260
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0004
- ADR-0006
- ADR-0012
governing_prds:
- PRD-0024
governing_stories:
- US-0075
target_release: 0.8.0
---

# TASK-0262: Interactive Merchant Haggling Engine with DM Arbitration Controls

## Status
Refined

## Summary
Implement a dynamic merchant bartering and haggling engine with a tug-of-war price meter, persuasive dialogue moves, merchant patience/temperament meters, and real-time DM arbitration controls for nudging moods, injecting custom dialogue barks, or overriding transaction terms.

## Problem Statement
Buying weapons, armor, bread, or potions in virtual tabletops is typically a static spreadsheet transaction. There is no participatory haggling minigame that balances player roleplay and charisma checks with merchant personalities, nor can the Game Master intervene in real time without halting the interface.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/run-tavern-minigames-and-merchant-haggling.md`: Personality-driven merchant bartering.
  - `docs/how-to/manage-dm-copilot-whispers-and-veto-overrides.md`: Human DM veto and narrative copilot overrides.
  - `docs/how-to/develop-lit-components-in-storybook.md`: Interactive negotiation drawer and Bauhaus token usage.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: DM role enforcement for transaction overrides and currency adjustments.
  - **ADR-0002: Domain Events via eventsource-py**: Immutable event audit log of bids, haggling moves, and closed deals.
  - **ADR-0004: Lit Web Components and Storybook UI**: Interactive negotiation drawer component.
  - **ADR-0006: Redis Streams Event Streaming**: Real-time negotiation event dispatch over WebSockets.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast price sliders and merchant patience meters.

## Product & User Story References
- **Product Requirement**: [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
- **User Story**: [`us-0075-dynamic-merchant-haggling-with-dm-arbitration.md`](../../user_stories/accepted/us-0075-dynamic-merchant-haggling-with-dm-arbitration.md)

## Detailed Specification & Implementation Plan
1. **Domain Logic & Valuation Rules (`services/game_session/src/game_session/settlement/haggling.py`)**:
   - `NegotiationSession`: Tracks original price, current offer, merchant base margin, patience points (1-5), and temperament modifiers (Greedy, Stubborn, Vain, Generous).
   - Bargaining Gambits: "Flattery / Praise", "Bulk Order Promise", "Point Out Flaw", "Hard Intimidation", "Walk Away Bluff".
   - Persuasion/Intimidation roll evaluation against merchant DC.
2. **DM Real-Time Control Panel (`frontend/src/components/dm-controls/`)**:
   - Live negotiation drawer allowing the DM to see current offers and merchant patience.
   - One-click mood modifiers: "Soothe Merchant", "Enrage Merchant", "Accept Deal", "Refuse & Kick Out".
   - Custom in-character bark injection field broadcasted via WebSockets.
3. **Frontend Component (`frontend/src/components/minigames/runefoble-merchant-haggler.ts`)**:
   - Responsive touch UI with sliding price scale, active dialogue cards, and merchant portrait emotion reaction.
4. **Frontdoor Blackbox Verification (`tests/test_blackbox_merchant_haggling.py`)**:
   - Execute gambit via HTTP/WebSocket frontdoor, assert price adjustment and patience score change.
   - DM override event closes transaction and credits inventory.

## INVEST Criteria Evaluation
- **Independent (I)**: Builds on top of `TASK-0260` worker model; operates independently of other minigames.
- **Negotiable (N)**: Specific gambit types and DC calculations can be tuned.
- **Valuable (V)**: Brings dynamic tabletop bartering to life with participatory player choices and DM tools.
- **Estimable (E)**: Pure negotiation state machine and UI drawer sized for a single pass.
- **Small (S)**: Kept under 300 lines per module.
- **Testable (T)**: Frontdoor API calls return clear negotiation responses and emit CloudEvents.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Bartering transactions deduct and credit player currency cleanly through domain events.
2. DM override immediately terminates or completes the exchange with zero race conditions.
3. Frontend negotiation drawer renders in Storybook across dark and light Bauhaus themes.
4. Blackbox frontdoor test suite passes via `uv run pytest tests/test_blackbox_merchant_haggling.py`.
5. All source files strictly under 400 lines per `AGENTS.md` Rule 6.
