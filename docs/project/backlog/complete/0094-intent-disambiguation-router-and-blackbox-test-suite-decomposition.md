---
id: 0094
title: Intent Disambiguation Router and Blackbox Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0054
governing_adrs:
- ADR-0002
- ADR-0003
- ADR-0007
- ADR-0009
target_release: 0.3.0
pr_url: https://github.com/tyevans/runefoble/pull/83
---
# TASK-0094: Intent Disambiguation Router and Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_intent_disambiguation.py` (458 lines, 91.6% of limit) and `services/the_watcher/src/the_watcher/routers/intent.py` (371 lines, 74.2% of limit) into specialized submodules and partitioned test suites before Hard Invariant 6 (File length limit < 500 lines) is breached.

## Problem Statement
`tests/test_blackbox_intent_disambiguation.py` spans 458 lines and verifies two complex, distinct capabilities introduced in TASK-0054:
1. Conversational intent disambiguation: Multi-target ambiguity detection (e.g., "Attack the goblin" with 3 goblins on the board), candidate token ghost preview emission, and player clarification resolution.
2. Compound action combo intents: Multi-step atomic action chains ("Move to (5,5) and cast Fireball at the troll"), sequential execution, rollback on failure, and combined audit event publication.

Similarly, `services/the_watcher/src/the_watcher/routers/intent.py` (371 lines) mixes single speech-to-intent parsing, multi-target disambiguation matching, and compound combo action pipeline routing in one module.

## Governing Architecture & ADRs
- **ADR-0002: The Watcher Autonomous DM**: Governs natural language understanding, disambiguation prompts, and intent extraction.
- **ADR-0003: UV Monorepo Workspace for Python Bounded Contexts**: Enforces clear module boundaries.
- **ADR-0007: Real-Time Voice and Board Synchronization**: Sub-500ms pipeline and tactile preview synchronization.
- **ADR-0009: Continuous Backlog Refinement and Technical Debt Management**: Preemptive refactoring before invariant limits.

## Proposed Decomposition
1. **Modular Intent Handlers (`services/the_watcher/src/the_watcher/routers/intent/`)**:
   - `disambiguation.py`: Ambiguity detection, clarification prompts, and target candidate matching (< 140 lines).
   - `compound.py`: Compound action combo parsing, atomic execution chains, and rollback handling (< 150 lines).
   - `__init__.py`: Primary APIRouter facade re-exporting existing `/intent` routes (< 60 lines).
2. **Modular Test Suites**:
   - `tests/test_blackbox_intent_disambiguation_flow.py`: Disambiguation requests, multiple target candidates, ghost preview events, and player clarification routes (< 230 lines).
   - `tests/test_blackbox_intent_compound_combos.py`: Multi-step compound actions, sequential execution, partial failure rollbacks, and CloudEvent validation (< 230 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal routing and test structure without altering external HTTP contracts or CloudEvent schemas (`IntentDisambiguationRequested`, `CompoundActionResolved`).
- **Negotiable (N)**: Split boundaries between intent helpers can be tailored for performance.
- **Valuable (V)**: Prevents invariant breaches (currently at 91.6% of limit) and improves test execution parallelism.
- **Estimable (E)**: Standard sub-router and pytest file extraction pattern.
- **Small (S)**: Scope strictly isolated to `the_watcher/routers/intent` and `tests/test_blackbox_intent_disambiguation.py`; all files < 240 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_blackbox_intent_*.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Sub-Routers**:
   - `services/the_watcher/src/the_watcher/routers/intent/` created with `disambiguation.py` and `compound.py`.
   - All router files strictly under 200 lines.
2. **100% Backward Compatibility**:
   - Zero change to `/api/v1/watcher/intent/*` route signatures and OpenAPI specs.
3. **Partitioned Test Suites**:
   - `tests/test_blackbox_intent_disambiguation_flow.py` and `tests/test_blackbox_intent_compound_combos.py` pass 100% of all existing tests.
   - All test files strictly under 250 lines.
4. **Quality Gates**:
   - Passes `uv run ruff check` and `uv run ruff format --check`.
