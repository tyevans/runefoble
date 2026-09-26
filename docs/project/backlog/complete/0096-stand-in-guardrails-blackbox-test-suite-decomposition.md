---
id: 0096
title: Stand-In Policy Guardrails and Hot-Swap Blackbox Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0055
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0003
- ADR-0009
target_release: 0.3.0
pr_url: https://github.com/tyevans/runefoble/pull/87
---
# TASK-0096: Stand-In Policy Guardrails and Hot-Swap Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_stand_in_guardrails.py` (369 lines, 73.8% of limit) into two focused blackbox test suites (`tests/test_blackbox_stand_in_policies.py` and `tests/test_blackbox_stand_in_takeover.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as autonomous tactics and persona profiles expand.

## Problem Statement
`tests/test_blackbox_stand_in_guardrails.py` currently spans 369 lines and verifies two independent subsystem workflows:
1. Tactical guardrail policies: Consumable spell slot restrictions, limited-use item locks, zero-HP unconscious stabilization overrides, and DM penalty compliance ("drunk", "foolishness").
2. Mid-session hot-swap handoff: Returning player presence detection, instantaneous token authority transfer, AI stand-in retirement, and audit CloudEvent emissions.

As absent player memory recaps (TASK-0011) and multi-party coordination advance, this monolithic test file risks breaching Hard Invariant 6.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Validates player token ownership and DM override authority.
- **ADR-0002: The Watcher Autonomous DM**: Governs stand-in decision-making boundaries.
- **ADR-0003: UV Monorepo Workspace for Python Bounded Contexts**: Standardizes module layout.
- **ADR-0009: Continuous Backlog Refinement and Technical Debt Management**: Preemptive refactoring.

## Proposed Decomposition
1. **Guardrail Policy Verification Suite (`tests/test_blackbox_stand_in_policies.py`)**:
   - High-level spell slot conservation, consumable protection, stabilization behavior at 0 HP, and penalty enforcement (< 190 lines).
2. **Hot-Swap Handoff & Session Takeover Suite (`tests/test_blackbox_stand_in_takeover.py`)**:
   - Player reconnection detection, hot-swap token handover, Zanzibar permission realignment, and CloudEvent publishing (< 190 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors test structure without changing any stand-in REST routes or aggregate behaviors.
- **Negotiable (N)**: Allocation of edge-case tests can be adjusted between suites.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and speeds up CI runs.
- **Estimable (E)**: Pure pytest separation with shared fixtures.
- **Small (S)**: Scope strictly isolated to `tests/test_blackbox_stand_in_guardrails.py`; all files < 200 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_blackbox_stand_in_*.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Test Suites**:
   - `tests/test_blackbox_stand_in_policies.py` and `tests/test_blackbox_stand_in_takeover.py` created with frontdoor setup.
   - All test files strictly under 200 lines.
2. **Complete Verification**:
   - 100% test pass rate across all existing stand-in guardrail and takeover test cases.
3. **Hard Invariant Compliance**:
   - Strictly conforms to Hard Invariant 6 (< 500 lines) and Hard Invariant 7 (public HTTP routes and CloudEvents).
4. **Quality Gates**:
   - Passes `uv run ruff check` and `uv run ruff format --check`.
