---
id: '0284'
title: Session Modal Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0249
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0007
- ADR-0012
governing_prds:
- PRD-0023
governing_stories:
- US-0065
- US-0067
target_release: 0.8.0
---

# TASK-0284: Session Modal Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_session_modal.py` (319 lines, 63.8% of limit) into modular test submodules under `tests/test_blackbox_session_modal/` (`conftest.py`, `test_invariants.py`, `test_component_contracts.py`, `test_gateway_session_api.py`), keeping all test files strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_session_modal.py` consolidates source file line invariants, Lit modal custom element lifecycle contracts, form fields/accessibility ARIA checks, Bauhaus design token verifications, and Gateway session scheduling API assertions in a monolithic 319-line file. As recurrent session scheduling, calendar integrations, and multi-lobby staging tests are introduced, this file will threaten the 500-line limit unless decomposed.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Fine-Grained Authorization**: Session creation and campaign membership checks.
- **ADR-0004: Lit Web Components and Storybook UI**: Accessible modal dialog contracts and Shadow DOM encapsulation.
- **ADR-0007: Domain-Driven Design Architecture**: Clean frontdoor testing over Gateway API.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: Bauhaus token compliance and high-contrast invariants.

## Scope of Work
1. **Shared Fixtures (`tests/test_blackbox_session_modal/conftest.py`)**:
   - Extract test client fixtures, store resets, and file path references (< 50 lines).
2. **Invariant & Token Tests (`tests/test_blackbox_session_modal/test_invariants.py`)**:
   - Extract source file length invariants and design token consumption checks (< 80 lines).
3. **Component Contracts & Form Fields (`tests/test_blackbox_session_modal/test_component_contracts.py`)**:
   - Extract custom element registration, accessibility ARIA, and form event handling assertions (< 90 lines).
4. **Gateway Session API Tests (`tests/test_blackbox_session_modal/test_gateway_session_api.py`)**:
   - Extract session scheduling, staging lobby creation, and campaign session listing frontdoor tests (< 110 lines).
5. **Verification**:
   - Remove root monolithic file and run `uv run pytest tests/test_blackbox_session_modal/`.

## Definition of Done
- `tests/test_blackbox_session_modal/` submodules strictly < 130 lines each.
- Monolithic `tests/test_blackbox_session_modal.py` safely removed.
- Passes all tests via `uv run pytest tests/test_blackbox_session_modal/`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
