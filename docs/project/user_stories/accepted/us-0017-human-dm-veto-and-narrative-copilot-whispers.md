---
id: 0017
title: Human DM Veto and Private Narrative Co-Pilot Whispers
status: Accepted
created: 2026-09-25
governing_prd: PRD-0001
---

# US-0017 — Human DM Veto and Private Narrative Co-Pilot Whispers

## Governing PRD
- [`PRD-0001: The Watcher AI Dungeon Master and Real-Time Board Animator`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)

## User Story

**As an** overworked human Dungeon Master (Evelyn),  
**I want to** receive private atmospheric hints and have instant veto/override power over AI DM rulings,  
**So that** The Watcher acts as my supportive co-pilot without undermining my creative authority or spoiling narrative secrets.

## Acceptance Criteria

1. **Private Co-Pilot Whispers**: The Watcher streams private narrative cues (secret NPC motivations, sensory details, perception checks) visible only to the DM.
2. **One-Click Veto**: The DM interface provides an instant "Veto" and "Edit" action on any generated AI action or monster movement before it commits to the board.
3. **Non-Blocking Fallback**: When the DM overrides an AI action, the system halts autonomous execution and yields turn arbitration immediately to the human DM.
4. **WebSocket Privacy**: Whispers and pending uncommitted AI suggestions are encrypted or filtered from player and spectator WebSocket channels.
