---
id: '0941'
title: The Reaction Prompt Receives Real Reactions From the Session
status: Proposed
created: 2026-11-19
dependencies:
- '0939'
governing_adrs:
- ADR-0013
- ADR-0014
governing_prds: []
governing_stories:
- us-0023-spoken-reaction-interrupts-and-ready-actions
target_bc: game_session
target_release: 0.9.0
---

# TASK-0941: The Reaction Prompt Receives Real Reactions From the Session

## Status

Proposed

## Summary

TASK-0939 made `<runefoble-combat-reaction-prompt>` idle by default and removed it from the default sidebar plugins, because no frame reaches the App Shell. The backend has `POST /api/v1/sessions/{id}/reactions/declare`, `GET /api/v1/sessions/{id}/reactions/active` (`services/game_session/src/game_session/routers/reactions.py`) and the `turn_paused_for_reaction` event. Wire them: a session frame for a paused turn, a read on load, the resolve and decline calls, and mount the prompt again.

## Source

`.audit/work/0939.md` (decision: remove the default entry, wiring is not small).
