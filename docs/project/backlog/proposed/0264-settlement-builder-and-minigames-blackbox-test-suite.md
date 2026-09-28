---
id: '0264'
title: Settlement Builder and Mobile Minigames Blackbox Test Suite
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0259
- TASK-0260
- TASK-0261
- TASK-0262
- TASK-0263
governing_adrs:
- ADR-0001
- ADR-0008
- ADR-0010
governing_prds:
- PRD-0024
governing_stories:
- US-0072
- US-0073
- US-0074
- US-0075
- US-0076
target_release: 0.8.0
---

# TASK-0264: Settlement Builder and Mobile Minigames Blackbox Test Suite

## Status
Proposed

## Summary
Author comprehensive blackbox test suites driving settlement founding, establishment configuration, NPC worker assignment, mobile tavern/casino minigame turns, merchant haggling arbitration, and bulletin board notice lifecycle strictly through public HTTP endpoints and WebSocket channels.

## Problem Statement
New settlement features, living NPC staff systems, and mobile web minigames must be rigorously verified against regression and concurrent race conditions. In accordance with `AGENTS.md` Rule 7, all tests must interact through public frontdoors rather than private internals.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/charter-frontier-settlements-and-havens.md`: Settlement tests.
  - `docs/how-to/run-tavern-minigames-and-merchant-haggling.md`: Minigame and bartering test patterns.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Verifying permissions across players, GMs, and spectators.
  - **ADR-0008: Property-Based and Blackbox Testing**: Frontdoor API and WebSocket verification.
  - **ADR-0010: Continuous Integration Pipeline**: Fast automated test execution in CI.

## Product & User Story References
- **Product Requirement**: [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
- **User Story**: [`us-0072-mobile-responsive-settlement-browser-and-town-builder.md`](../../user_stories/accepted/us-0072-mobile-responsive-settlement-browser-and-town-builder.md)
- **User Story**: [`us-0073-customizable-establishments-and-assignable-npc-workers.md`](../../user_stories/accepted/us-0073-customizable-establishments-and-assignable-npc-workers.md)
- **User Story**: [`us-0074-interactive-mobile-tavern-and-casino-minigames.md`](../../user_stories/accepted/us-0074-interactive-mobile-tavern-and-casino-minigames.md)
- **User Story**: [`us-0075-dynamic-merchant-haggling-with-dm-arbitration.md`](../../user_stories/accepted/us-0075-dynamic-merchant-haggling-with-dm-arbitration.md)
- **User Story**: [`us-0076-town-bulletin-board-civic-rumors-and-bounties.md`](../../user_stories/accepted/us-0076-town-bulletin-board-civic-rumors-and-bounties.md)

## Detailed Specification & Implementation Plan
1. **API Frontdoor Tests (`tests/test_settlements_blackbox.py`)**:
   - `test_found_settlement_and_upgrade_tier_flow`: Test founding, verifying district slot caps per scale.
   - `test_establishment_creation_and_worker_assignment`: Place weaponsmith, assign NPC armorer, verify dynamic inventory.
   - `test_merchant_haggling_gambits_and_dm_override`: Simulate persuasion rolls against merchant temperament and verify DM mood adjustment endpoint.
   - `test_bulletin_board_pin_and_cipher_decrypt`: Post bounty, decrypt hidden notice, verify WebSocket broadcast.
2. **WebSocket Minigame Synchronization Tests (`tests/test_minigames_websocket.py`)**:
   - `test_darts_and_billiards_multiplayer_turn_sync`: Multiple player connections exchanging touch trajectory vectors.
   - `test_casino_craps_and_roulette_betting_and_payouts`: Wager placement, dice tumble resolution, and character coin purse crediting.
3. **File Length & Code Quality Invariants**:
   - Split test files if approaching 350 lines to strictly respect `AGENTS.md` Rule 6.

## Definition of Done
- 100% of new settlement and minigame features covered by frontdoor blackbox tests.
- All test suites execute cleanly and deterministically in under 5 seconds.
- Zero private state manipulation or backdoor mocking of aggregate state.
