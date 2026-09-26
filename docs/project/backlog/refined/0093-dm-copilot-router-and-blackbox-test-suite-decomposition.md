---
id: 0093
title: DM Co-Pilot Router and Blackbox Test Suite Modular Decomposition
status: in-progress
created: 2026-09-26
dependencies:
- TASK-0053
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0003
- ADR-0009
- ADR-0013
target_release: 0.3.0
claimed_by: worker-0093
branch: feat/0093-dm-copilot-router-and-blackbox-test-suite-decomposition
---
# TASK-0093: DM Co-Pilot Router and Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_dm_copilot.py` (474 lines, 94.8% of limit) and `services/the_watcher/src/the_watcher/routers/copilot.py` (399 lines, 79.8% of limit) into modular sub-routers and partitioned test suites before Hard Invariant 6 (File length limit < 500 lines) is breached as spectator whispers and cinematic camera cues expand.

## Problem Statement
`tests/test_blackbox_dm_copilot.py` currently spans 474 lines—only 26 lines away from violating the repository's hard file length limit (Hard Invariant 6). It tests two distinct feature branches in a single monolithic file:
1. Narrative whisper suggestions: Private whisper creation, LLM narrative prompt generation, unread whisper tracking, and SpiceDB Zanzibar DM permission enforcement.
2. AI DM pre-execution pause window and veto overrides: AI action proposal, pause window timeouts, DM approvals, DM parameter mutations, and hard veto rejections with CloudEvent emissions.

Similarly, `services/the_watcher/src/the_watcher/routers/copilot.py` (399 lines) mixes both whisper REST endpoints and action proposal/veto state management into a single router.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Enforces fine-grained `dungeon_master` permissions on all whisper and veto override endpoints.
- **ADR-0002: The Watcher Autonomous DM**: Governs the DM co-pilot assistant loop and human veto authority.
- **ADR-0003: UV Monorepo Workspace for Python Bounded Contexts**: Standardizes modular package boundaries.
- **ADR-0009: Continuous Backlog Refinement and Technical Debt Management**: Mandates proactive decomposition before the 500-line limit is reached.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Preserves microfrontend manifest exposure.

## Proposed Decomposition
1. **Copilot Sub-Routers (`services/the_watcher/src/the_watcher/routers/copilot/`)**:
   - `whispers.py`: Private narrative whisper creation, list, and unread status endpoints (< 150 lines).
   - `actions.py`: AI action proposal, pause window countdown, approve, modify, and veto override endpoints (< 180 lines).
   - `__init__.py`: Combined APIRouter re-exporting `/copilot` routes with 100% backward compatibility (< 40 lines).
2. **Blackbox Test Suite Modularization**:
   - `tests/test_blackbox_dm_copilot_whispers.py`: Blackbox TDD coverage for whisper generation, unread listing, and Zanzibar DM authorization (< 220 lines).
   - `tests/test_blackbox_dm_copilot_actions.py`: Blackbox TDD coverage for action proposal, pause window lifecycle, veto/approval CloudEvents, and parameter modification (< 240 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal copilot module structure and test organization without changing external HTTP API endpoints, request schemas, or CloudEvent payloads.
- **Negotiable (N)**: Split boundaries between sub-router modules can be adjusted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (at 94.8% of limit) and improves test isolation and speed.
- **Estimable (E)**: Follows the established APIRouter and test decomposition pattern.
- **Small (S)**: Scope strictly isolated to `the_watcher/routers/copilot` and `tests/test_blackbox_dm_copilot.py`; all resulting files < 250 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_blackbox_dm_copilot*.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Sub-Routers**:
   - `services/the_watcher/src/the_watcher/routers/copilot/` created with `whispers.py`, `actions.py`, and clean package exports.
   - All router files strictly under 250 lines.
2. **Backward Compatibility**:
   - Zero change to public HTTP endpoint paths (`/api/v1/watcher/copilot/*`) and OpenAPI schema.
3. **Partitioned Test Suites**:
   - `tests/test_blackbox_dm_copilot_whispers.py` and `tests/test_blackbox_dm_copilot_actions.py` operational with frontdoor setup.
   - 100% test pass rate across all 15 existing copilot test scenarios.
   - All test files strictly under 260 lines.
4. **Quality Gates**:
   - Passes `uv run ruff check` and `uv run ruff format --check`.
