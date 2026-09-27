---
id: '0182'
title: Watcher Domain Events Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0155
- TASK-0156
- TASK-0157
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0001
- PRD-0004
- PRD-0007
governing_stories:
- US-0018
- US-0020
- US-0023
target_release: 0.7.0
---

# TASK-0182: Watcher Domain Events Modular Decomposition

## Status
Proposed

## Summary
Decompose `libs/runefoble_events/src/runefoble_events/watcher.py` (364 lines, 72.8% of limit) by modularizing speech, narration, dice, reaction, and vocal modulation domain events into focused submodules, keeping all modules strictly < 200 lines per Hard Invariant 6.

## Problem Statement
`libs/runefoble_events/src/runefoble_events/watcher.py` has grown to 364 lines as new capabilities (reactions, spoken traps, and vocal modulation presets) added domain events to this file. As Milestone 9 introduces additional speech interruption and barge-in events, this file is rapidly approaching the 400+ warning limit and the 500-line hard ceiling.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean package structure across shared core libraries.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Event schemas and stream topic definitions.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for event schemas across bounded contexts.

## Scope of Work
1. **Speech and Narration Events (`libs/runefoble_events/src/runefoble_events/watcher_narrative.py`)**:
   - Extract `PlayerSpokeEvent`, `SpeechIntentParsed`, `WatcherNarrationGenerated`, and `StandInActionDecided` (< 120 lines).
2. **Combat & Reaction Events (`libs/runefoble_events/src/runefoble_events/watcher_combat.py`)**:
   - Extract `DiceRolled`, `ReactionPromptTriggered`, `ReactionOpportunityResolved`, `SecretTrapTriggered`, and `VocalModulatorPresetChanged` (< 150 lines).
3. **Watcher Re-export Facade (`libs/runefoble_events/src/runefoble_events/watcher.py`)**:
   - Preserve backward-compatible imports while reducing `watcher.py` to < 80 lines.
4. **Verification**:
   - Ensure all event registrations and imports throughout the workspace continue to resolve without breaking changes.
   - Run `uv run pytest tests/` to confirm zero regression.

## Definition of Done
- `watcher.py` reduced to < 100 lines.
- All newly extracted event submodules strictly < 200 lines.
- All workspace tests pass via `uv run pytest`.
- Linting and formatting pass via `uv run ruff check .` and `uv run ruff format --check .`.
