---
id: 0182
title: Watcher Domain Events Modular Decomposition
status: Complete
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
pr_url: https://github.com/tyevans/runefoble/pull/241
---
# TASK-0182: Watcher Domain Events Modular Decomposition

## Status
Refined

## Summary
Decompose `libs/runefoble_events/src/runefoble_events/watcher.py` (364 lines, 72.8% of limit) by modularizing speech, narration, dice, reaction, and vocal modulation domain events into focused submodules under `libs/runefoble_events/src/runefoble_events/watcher_events/`, keeping all modules strictly < 150 lines per Hard Invariant 6 and ADR-0007.

## Problem Statement
`libs/runefoble_events/src/runefoble_events/watcher.py` has grown to 364 lines as new capabilities (reactions, spoken traps, and vocal modulation presets) added domain events to this file. As Milestone 9 introduces additional speech interruption and barge-in events, this file is rapidly approaching the 400+ warning limit and the 500-line hard ceiling.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean package structure across shared core libraries.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Event schemas and stream topic definitions.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for event schemas across bounded contexts.

## Detailed Specification & Implementation Plan
1. **Speech and Narration Events (`libs/runefoble_events/src/runefoble_events/watcher_events/narrative.py`)**:
   - Extract `PlayerSpokeEvent`, `SpeechIntentParsed`, `WatcherNarrationGenerated`, and `StandInActionDecided` (< 120 lines).
2. **Combat & Reaction Events (`libs/runefoble_events/src/runefoble_events/watcher_events/combat.py`)**:
   - Extract `DiceRolled`, `ReactionPromptTriggered`, `ReactionOpportunityResolved`, `SecretTrapTriggered`, and `VocalModulatorPresetChanged` (< 150 lines).
3. **Watcher Re-export Facade (`libs/runefoble_events/src/runefoble_events/watcher.py`)**:
   - Preserve backward-compatible imports while reducing `watcher.py` to < 60 lines.
4. **Verification**:
   - Ensure all event registrations and imports throughout the workspace continue to resolve without breaking changes.
   - Run `uv run pytest tests/` to confirm zero regression.

## INVEST Criteria Evaluation
- **Independent (I)**: Event schema modularization with backward-compatible re-exports across consuming services.
- **Negotiable (N)**: Submodule taxonomy (narrative vs combat vs voice) can be adjusted to balance line lengths.
- **Valuable (V)**: Safeguards against Hard Invariant 6 (500 lines) and organizes Watcher events logically.
- **Estimable (E)**: Pure refactoring with explicit event registration decorators preserved.
- **Small (S)**: Bounded strictly to `libs/runefoble_events/src/runefoble_events/`; all modules < 150 lines.
- **Testable (T)**: Frontdoor verification through workspace event serialization and blackbox integration tests.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `watcher.py` re-export facade reduced to strictly < 80 lines.
   - Extracted submodules under `watcher_events/` strictly < 150 lines each.
2. **Frontdoor Test Verification**:
   - All workspace tests pass via `uv run pytest tests/test_autonomous_dm.py tests/test_blackbox_reaction_prompts/`.
3. **Quality Gates**:
   - Code passes `uv run ruff check .` and `uv run ruff format --check .`.
