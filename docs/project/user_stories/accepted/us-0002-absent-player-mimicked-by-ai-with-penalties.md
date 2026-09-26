---
id: 0002
title: Autonomous Stand-In for Absent Player with DM Penalties
status: Accepted
created: 2026-09-25
governing_prd: PRD-0002
---

# US-0002 — Autonomous Stand-In for Absent Player with DM Penalties

## Governing PRD
- [`PRD-0002: Missing Player AI Stand-In with Mimicry and Absence Costs`](../../product/accepted/prd-0002-missing-player-ai-stand-in-with-penalties.md)

## User Story

**As a** gaming group with one missing member,
**I want** The Watcher AI to pilot their character with personality mimicry and DM-inflicted penalties (e.g. "Drunk", "Foolishness"),
**So that** our scheduled session is not canceled and the absence adds memorable humor and narrative flavor to the adventure.

## Acceptance Criteria

1. **Absence Designation**: The DM or absent player marks the character as "AI Stand-in" for the session.
2. **Penalty Selection**: The DM selects or rolls for a session miss cost:
   - "Drunk": +2 Bravery, -2 Perception, slurred voice lines, disadvantage on dexterity saves.
   - "Foolishness": AI takes brazen tactical risks and boasts grandly.
3. **Turn Automation**: When the stand-in's turn arrives in the initiative order, the AI announces their action in voice/chat and takes their turn.
4. **Session Log Recap**: When the human player returns next week, they receive an audio/text recap summarizing their character's exploits.
