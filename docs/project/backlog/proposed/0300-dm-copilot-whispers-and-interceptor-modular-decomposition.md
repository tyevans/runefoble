---
id: '0300'
title: DM Copilot Narrative Whispers and Interceptor Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0053
governing_adrs:
- ADR-0002
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0004
governing_stories:
- US-0020
- US-0025
target_release: 0.8.0
---

# TASK-0300: DM Copilot Narrative Whispers and Interceptor Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/the_watcher/src/the_watcher/copilot.py` (301 lines, 60.2% of limit) into modular submodules under `services/the_watcher/src/the_watcher/copilot/` (`whispers.py`, `interceptor.py`, `engine.py`, `__init__.py`), keeping each submodule strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`services/the_watcher/src/the_watcher/copilot.py` currently couples two distinct responsibilities into a single 301-line module:
1. Private DM whisper narrative generation, history storage, and prompt framing.
2. AI action proposal interception, veto countdown timer scheduling, callback execution, and manual overrides.

As secret DM triggers, dynamic spectator whisper pools, and complex rollbacks are added, this file will rapidly approach the 500-line invariant limit unless partitioned into focused submodules.

## Governing Architecture & ADRs
- **ADR-0002: CloudEvents 1.0 Domain Events**: Emits veto and action execution events.
- **ADR-0007: Domain-Driven AI DM Co-Pilot Engine**: Decouples whisper suggestion generation from action interceptors.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 130 lines).

## Scope of Work
1. **Narrative Whispers Manager (`services/the_watcher/src/the_watcher/copilot/whispers.py`)**:
   - Extract whisper storage, retrieval, and contextual default generator methods (< 110 lines).
2. **Action Interceptor & Veto Timer (`services/the_watcher/src/the_watcher/copilot/interceptor.py`)**:
   - Extract pending action registration, async countdown timer tasks, veto resolution, and execution callbacks (< 120 lines).
3. **Co-Pilot Engine Orchestrator (`services/the_watcher/src/the_watcher/copilot/engine.py` & `__init__.py`)**:
   - Unify whispers and interceptors into the `CopilotEngine` facade for 100% backwards compatibility (< 80 lines).
4. **Verification**:
   - Run `uv run pytest tests/test_blackbox_dm_copilot.py` and `uv run pytest tests/test_blackbox_dm_copilot/` to ensure all tests pass cleanly.

## Definition of Done
- `services/the_watcher/src/the_watcher/copilot.py` decomposed into `services/the_watcher/src/the_watcher/copilot/` package.
- All extracted submodules strictly < 130 lines per Hard Invariant 6.
- 100% backwards compatibility preserved for `from the_watcher.copilot import CopilotEngine`.
- Passes all DM copilot blackbox tests.
