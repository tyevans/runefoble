---
id: 0053
title: DM Co-Pilot Whisper Prompts and Veto Override Engine
status: Proposed
created: 2026-09-25
dependencies: [TASK-0002, TASK-0013, TASK-0016]
governing_adrs: [ADR-0002, ADR-0007]
target_release: 0.2.1
---

# TASK-0053: DM Co-Pilot Whisper Prompts and Veto Override Engine

## Status
Proposed

## Summary
Implement private DM whisper channels and instant veto/override mechanics in `services/the_watcher` and the frontend, allowing human DMs (Evelyn) to intercept or edit AI-proposed actions before execution.

## Problem Statement
While ADR-0002 mandates that "The Watcher is an assistant, never a dictator", there is currently no real-time veto interface or private whisper pipeline to suggest narrative ideas to human DMs without revealing them to players.

## Scope of Work
1. **Private Whisper Channel**: Add encrypted DM-only narrative stream in `the_watcher` for atmospheric hints, secrets, and passive checks.
2. **Veto Interceptor**: Introduce a 2-second pre-execution pause window for human DMs with instant "Veto", "Edit", or "Approve" controls.
3. **Frontend DM Screen Action Bar**: Add Lit components for one-click veto and action editing.

## Acceptance Criteria
1. Whispers are visible only to users with the `dm` role in SpiceDB Zanzibar.
2. DM veto immediately aborts action execution on `board_state` and returns initiative control to the DM.
3. Edited actions commit with modified parameters without error.
