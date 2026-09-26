---
id: 0054
title: Conversational Disambiguation and Compound Action Intents
status: Proposed
created: 2026-09-25
dependencies: [TASK-0002, TASK-0027]
governing_adrs: [ADR-0007, ADR-0009]
target_release: 0.2.1
---

# TASK-0054: Conversational Disambiguation and Compound Action Intents

## Status
Proposed

## Summary
Extend `services/the_watcher` and `services/inference_worker` intent parsing to support multi-part tactical combos and conversational target disambiguation for voice-first players (Marcus).

## Problem Statement
When a player speaks an ambiguous command ("I strike the cultist" when multiple cultists are present) or a compound action ("I jump the table and hit the ogre"), the current single-shot intent parser either fails or arbitrarily guesses.

## Scope of Work
1. **Target Disambiguation Graph**: Detect ambiguous target references in `stand_in_graph` / `speech_to_intent` and return clarifying audio/visual prompts.
2. **Compound Action Decomposition**: Parse chained verbs into sequential action graphs (movement -> skill check -> attack).
3. **Ghost Path Rendering**: Emit preview path events to `board_state` highlighting threat zones during verbal clarification.

## Acceptance Criteria
1. Clarification prompts return within 400ms when targets are ambiguous.
2. Compound actions resolve in strict sequential order without desynchronizing combat state.
3. Full integration tests covering multi-step intent execution.
