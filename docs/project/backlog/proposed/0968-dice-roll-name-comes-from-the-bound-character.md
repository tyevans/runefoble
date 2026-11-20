---
id: '0968'
title: The Dice Roll Name Comes From the Caller's Bound Character, Not From the Client
status: Proposed
created: 2026-11-19
dependencies:
- '0951'
governing_adrs:
- ADR-0015
- ADR-0001
governing_prds:
- PRD-0025
governing_stories: []
target_bc: game_session
target_release: 1.0.0
---

# TASK-0968: The Dice Roll Name Comes From the Caller's Bound Character, Not From the Client

## Status

Proposed

## Summary

Since TASK-0951 the roller posts `roller_name` to `POST /api/v1/sessions/{id}/roll` (`services/game_session/ui/src/dice-roll-api.ts`). The roller identity comes from the bearer, but the name shown in every player's chronicle is the text the client sent. A player can make a roll appear under any name. game_session must take the name from the character that the caller has in the session seat, and ignore or refuse a client name.

## Test Plan

- Pytest through the gateway: a roll with a `roller_name` that differs from the caller's seated character shows the seated character's name in the reply, the `DiceRolled` event and the chronicle.
