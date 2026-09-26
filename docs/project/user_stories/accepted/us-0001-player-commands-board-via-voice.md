---
id: 0001
title: Spoken Tactical Board Manipulation
status: Accepted
created: 2026-09-25
governing_prd: PRD-0001
---

# US-0001 — Spoken Tactical Board Manipulation

## Governing PRD
- [`PRD-0001: The Watcher AI Dungeon Master and Real-Time Board Animator`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)

## User Story

**As a** tabletop player in an active encounter,
**I want to** speak naturally to move my character token across the tactical map ("Valeros strides three squares forward"),
**So that** I stay immersed in the collaborative story without breaking eye contact or fumbling with map coordinates.

## Acceptance Criteria

1. **Natural Speech Recognition**: Spoken phrases stating direction and distances (e.g., "charge 2 spaces east", "fall back 1 square south") are correctly transcribed and parsed.
2. **Visual Feedback**: The tactical board highlights the token, moves it to the target cell, and updates fog-of-war within 500ms.
3. **Turn Validation**: If it is not the player's turn, or the move exceeds movement speed, The Watcher gently prompts the player or queues the intent.
4. **Narrative Chronicle**: The action is broadcast over WebSockets and added to the collaborative chronicle feed.
