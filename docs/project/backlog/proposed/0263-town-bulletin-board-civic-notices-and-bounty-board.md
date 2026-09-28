---
id: '0263'
title: Town Bulletin Board, Civic Proclamations, and Rumor Network
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0259
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0012
governing_prds:
- PRD-0024
governing_stories:
- US-0076
target_release: 0.8.0
---

# TASK-0263: Town Bulletin Board, Civic Proclamations, and Rumor Network

## Status
Proposed

## Summary
Implement the interactive Town Bulletin Board component and domain projection, allowing players and DMs to pin notices, monster bounties, mercantile job postings, tavern rumors, and secret cipher mini-puzzles to community gathering squares and tavern common rooms.

## Problem Statement
Settlements lack a tangible, diegetic community communication hub. Rumors and quests are currently presented as out-of-character journal entries or verbal DM exposition, missing the immersive flavor of physical corkboard notices, wax-sealed proclamations, and hidden flyer ciphers.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/post-and-fulfill-mercenary-bounty-contracts.md`: Bounty escrow and contract posting.
  - `docs/how-to/inspect-diegetic-handouts-and-3d-relics.md`: Parchment handouts and wax seal physics.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Campaign member permissions for pinning public vs party-private notices.
  - **ADR-0004: Lit Web Components and Storybook UI**: Skeuomorphic wooden board component.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast notice cards with authentic parchment typography.

## Product & User Story References
- **Product Requirement**: [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
- **User Story**: [`us-0076-town-bulletin-board-civic-rumors-and-bounties.md`](../../user_stories/accepted/us-0076-town-bulletin-board-civic-rumors-and-bounties.md)

## Detailed Specification & Implementation Plan
1. **Domain Events & Projections (`libs/runefoble_events/bulletin.py`)**:
   - `BulletinNoticePinned`: `notice_id`, `settlement_id`, `board_type` (town_square, tavern, guildhall), `title`, `author_id`, `category` (bounty, rumor, ordinance, job), `content`, `wax_sealed`, `cipher_encoded`.
   - `BulletinNoticeRemoved`: `notice_id`, `remover_id`.
   - `CipherNoticeDecrypted`: `notice_id`, `player_id`.
2. **Frontend Component (`frontend/src/components/runefoble-bulletin-board.ts`)**:
   - Corkboard/wood textured canvas with pinned parchment cards.
   - Interactive modal on tap to expand notice details with acoustic paper rustle.
   - Built-in mini-puzzle overlay for decrypting Thieves' Cant or ancient rune ciphers.
3. **Player & DM Interactions**:
   - "+ Pin Notice" button allowing players to post bounties or requests.
   - DM tools for spawning mysterious flyers or town crier decrees.

## Definition of Done
- Pinned notices persist in the settlement read projection and update connected viewers via WebSockets.
- Cipher mini-game successfully unlocks secret quest text upon completion.
- Storybook stories verify empty state, pinned cards, and modal inspection.
- Files remain strictly under 400 lines.
