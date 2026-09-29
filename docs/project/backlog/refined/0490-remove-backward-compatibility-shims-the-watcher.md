---
id: '0490'
title: Remove Backward Compatibility Shims & Re-exports in the_watcher
status: Refined
created: 2026-09-29
dependencies:
- TASK-0002
- TASK-0003
- TASK-0013
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0002
- PRD-0003
governing_stories:
- US-0002
- US-0003
target_release: 0.9.0
---

# TASK-0490: Remove Backward Compatibility Shims & Re-exports in the_watcher

## Status
Refined

## Summary
Decommission and remove backward-compatibility facades and legacy method aliases in `services/the_watcher` (`autonomous_dm.py` facade, `stand_in_ai.py` facade, and `SpeechIntentParser` backward-compatible methods), migrating all callers and tests directly to modular domain components.

## Problem Statement
When The Watcher was decomposed into focused submodules (such as modular copilot routers, stand-in guardrails, and intent processors), legacy facade files (`autonomous_dm.py` and `stand_in_ai.py`) were retained in `services/the_watcher/src/the_watcher/` to forward calls to underlying sub-modules. Additionally, `SpeechIntentParser` retains legacy parser methods tested for backward compatibility in `tests/test_movement_parser.py:test_parser_backward_compatible_methods`. Under the updated DoR, these facades and compatibility shims must be excised.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/explanation/the-watcher-autonomous-dm.md`: Autonomous DM architecture and intent processing.
  - `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md`: Guardrails and stand-in mechanics.
- **Governing Architecture & ADRs**:
  - **ADR-0007: Speech-to-Intent Pipeline**: Sub-500ms voice intent processing.
  - **ADR-0013: Frontend Microfrontend Architecture**: Microfrontend component vendoring.

## Product & User Story References
- [`prd-0002-missing-player-ai-stand-in-with-penalties.md`](../../product/accepted/prd-0002-missing-player-ai-stand-in-with-penalties.md)
- [`prd-0003-the-watcher-autonomous-dm-engine.md`](../../product/accepted/prd-0003-the-watcher-autonomous-dm-engine.md)
- [`us-0002-autonomous-dm-intent-arbitration.md`](../../user_stories/accepted/us-0002-autonomous-dm-intent-arbitration.md)
- [`us-0003-missing-player-tactical-stand-in.md`](../../user_stories/accepted/us-0003-missing-player-tactical-stand-in.md)

## Detailed Specification & Implementation Plan
1. **Decommission Facade Files**:
   - Refactor callers of `the_watcher.autonomous_dm` to import directly from orchestration submodules (`the_watcher.orchestration` / `the_watcher.copilot`), then remove the facade wrapper.
   - Refactor callers of `the_watcher.stand_in_ai` to import directly from `the_watcher.stand_in_guardrails`, `the_watcher.persona`, and `the_watcher.recap`, then remove `stand_in_ai.py` facade.
2. **Remove Compatibility Methods in Parser**:
   - In `services/the_watcher/src/the_watcher/movement_parser.py` (or intent parser), remove legacy wrapper methods that duplicate canonical intent extraction.
3. **Update Blackbox Test Suites**:
   - In `tests/test_movement_parser.py`, remove `test_parser_backward_compatible_methods()`.
   - Update `tests/test_autonomous_dm*.py` and `tests/test_stand_in_ai*.py` to invoke authoritative modules directly.
4. **Clean Up `__init__.py`**:
   - Ensure `the_watcher/__init__.py` re-exports only current primary interfaces with zero deprecated aliases.

## INVEST Criteria Evaluation
- **Independent (I)**: Changes are contained within `services/the_watcher` and its test suites.
- **Negotiable (N)**: Clean modular direct imports.
- **Valuable (V)**: Eliminates 2 major facade files and redundant wrapper methods.
- **Estimable (E)**: Identified files (`autonomous_dm.py`, `stand_in_ai.py`, parser methods).
- **Small (S)**: File deletions and caller updates conforming to < 500 lines per file.
- **Testable (T)**: Verified by `uv run pytest tests/test_movement_parser.py tests/test_autonomous_dm*`.

## Definition of Done
1. `autonomous_dm.py` and `stand_in_ai.py` facade wrappers removed.
2. Legacy parser wrapper methods removed.
3. Call sites and tests migrated to modular submodules.
4. Obsolete backward-compatibility tests removed.
5. All The Watcher test suites pass cleanly.
