---
id: 0018
title: Secret DM Traps, Map Switching, and Stage Triggers
status: Accepted
created: 2026-09-25
---

# US-0018 — Secret DM Traps, Map Switching, and Stage Triggers

## User Story

**As a** Dungeon Master running complex dungeon crawls (Evelyn),  
**I want to** place hidden trap triggers and seamlessly switch tactical maps mid-session,  
**So that** I can spring dramatic spatial surprises on the party and move between scenes without pausing game night.

## Acceptance Criteria

1. **DM Hidden Layer**: Secret doors, traps, and ambush markers are visible only on the DM's client view and masked from player fog-of-war.
2. **Spatial Trigger Detection**: When a player token steps into a trap cell, movement automatically pauses and alerts the DM before triggering mechanical consequences.
3. **Mid-Session Map Switch**: Evelyn can switch the active battlemap in `board_state` and batch-teleport all party tokens to new spawn coordinates in a single transaction.
