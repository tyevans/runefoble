---
id: '0263'
title: Town Bulletin Board, Civic Proclamations, and Rumor Network
status: Complete
created: 2026-09-27
dependencies:
- TASK-0259
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0004
- ADR-0006
- ADR-0012
governing_prds:
- PRD-0024
governing_stories:
- US-0076
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/300
---
# TASK-0263: Town Bulletin Board, Civic Proclamations, and Rumor Network

## Status
Refined

## Summary
Implement the interactive Town Bulletin Board component and domain projection, allowing players and DMs to pin notices, monster bounties, mercantile job postings, tavern rumors, and secret cipher mini-puzzles to community gathering squares and tavern common rooms with real-time WebSocket broadcast and SpiceDB Zanzibar authorization.

## Problem Statement
Settlements lack a tangible, diegetic community communication hub. Rumors and quests are currently presented as out-of-character journal entries or verbal DM exposition, missing the immersive flavor of physical corkboard notices, wax-sealed proclamations, and hidden flyer ciphers. Furthermore, players need an in-world channel to post bounties and trade contracts with escrow and live party updates.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/post-and-fulfill-mercenary-bounty-contracts.md`: Bounty escrow and contract posting workflows.
  - `docs/how-to/inspect-diegetic-handouts-and-3d-relics.md`: Parchment handouts and wax seal physics.
  - `docs/how-to/develop-lit-components-in-storybook.md`: Lit component structure and Bauhaus design token usage.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Campaign member permissions for pinning public vs party-private notices and DM moderation.
  - **ADR-0002: Domain Events via eventsource-py**: Immutable event audit log of notices pinned, completed, or removed.
  - **ADR-0004: Lit Web Components and Storybook UI**: Skeuomorphic wooden board component with responsive touch interaction.
  - **ADR-0006: Redis Streams Event Streaming**: Real-time WebSocket synchronization across active table and mobile clients.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast notice cards with authentic parchment typography.

## Product & User Story References
- **Product Requirement**: [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
- **User Story**: [`us-0076-town-bulletin-board-civic-rumors-and-bounties.md`](../../user_stories/accepted/us-0076-town-bulletin-board-civic-rumors-and-bounties.md)

## Detailed Specification & Implementation Plan
1. **Domain Events & Projections (`libs/runefoble_events/src/runefoble_events/settlements.py`)**:
   - `BulletinNoticePinnedEvent`: `notice_id`, `settlement_id`, `board_type` (town_square, tavern, guildhall), `title`, `author_id`, `category` (bounty, rumor, ordinance, job), `content`, `wax_sealed`, `cipher_encoded`.
   - `BulletinNoticeRemovedEvent`: `notice_id`, `settlement_id`, `remover_id`.
   - `CipherNoticeDecryptedEvent`: `notice_id`, `settlement_id`, `player_id`.
2. **FastAPI Endpoints (`services/game_session/src/game_session/settlement/router.py`)**:
   - `POST /api/v1/settlements/{id}/bulletin`: Pin new notice (enforcing Zanzibar `view` and `edit` relations).
   - `GET /api/v1/settlements/{id}/bulletin`: Retrieve active notices for settlement and board type.
   - `DELETE /api/v1/settlements/{id}/bulletin/{notice_id}`: Remove or fulfill notice.
   - `POST /api/v1/settlements/{id}/bulletin/{notice_id}/decrypt`: Submit cipher solution and reveal hidden text.
3. **Frontend Component (`frontend/src/components/runefoble-bulletin-board.ts`)**:
   - Corkboard/wood textured canvas with pinned parchment cards.
   - Interactive modal on tap to expand notice details with acoustic paper rustle.
   - Built-in mini-puzzle overlay for decrypting Thieves' Cant or ancient rune ciphers.
4. **Frontdoor Blackbox Verification (`tests/test_blackbox_bulletin_board.py`)**:
   - Pin notice via HTTP POST, assert event broadcast and retrieval in GET list.
   - Decrypt cipher notice, verify decrypted content returned to authorized player.

## INVEST Criteria Evaluation
- **Independent (I)**: Operates independently within settlement boundaries, building on `TASK-0259`.
- **Negotiable (N)**: Cipher mini-puzzle types and visual styles can be customized.
- **Valuable (V)**: Gives parties an immersive in-game notice board for contracts, rumors, and lore.
- **Estimable (E)**: Standard CRUD router, event models, and Lit component sized for a single pass.
- **Small (S)**: Component and router changes each kept under 250 lines.
- **Testable (T)**: Directly testable through FastAPI endpoints and emitted Redis domain events.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Pinned notices persist in settlement state and synchronize to connected viewers via WebSockets.
2. Cipher mini-game successfully unlocks secret quest text upon valid decryption submission.
3. Storybook stories verify empty state, pinned cards, and modal inspection across themes.
4. Blackbox tests pass via `uv run pytest tests/test_blackbox_bulletin_board.py`.
5. All source files strictly under 400 lines per `AGENTS.md` Rule 6.
