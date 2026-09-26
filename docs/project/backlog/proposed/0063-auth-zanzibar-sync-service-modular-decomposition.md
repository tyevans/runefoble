---
id: '0063'
title: Zanzibar Auth Relationship Sync Service and Event Handlers Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0008, TASK-0032]
governing_adrs: [ADR-0001, ADR-0003]
target_release: 0.2.0
---

# TASK-0063: Zanzibar Auth Relationship Sync Service and Event Handlers Modular Decomposition

## Status
Proposed

## Summary
Decompose `libs/runefoble_auth/src/runefoble_auth/sync.py` (392 lines, 78.4% of limit) into modular submodules (`sync_tuples.py`, `sync_events.py`, `sync.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as new Zanzibar schema relations and domain event integrations are added.

## Problem Statement
`libs/runefoble_auth/src/runefoble_auth/sync.py` currently spans 392 lines and combines three distinct layers of responsibility:
1. Low-level SpiceDB relationship tuple formatting, role normalization, and error handling (`SyncResult`, `_write_tuple`, `_delete_tuple`).
2. High-level identity and resource entity binding methods (`sync_user_registration`, `sync_membership`, `sync_character_ownership`, `sync_session_campaign`, `sync_board_token`).
3. Asynchronous domain event ingestion and event-to-tuple dispatching (`handle_domain_event` routing CloudEvents such as `SessionCreated`, `CharacterCreated`, `TokenPlacedOnBoard`).

As Milestone 2 connects production SpiceDB gRPC clients and schema migrations (TASK-0035), and subsequent milestones introduce encounter, lore, and spectator relationships, this file will rapidly exceed 500 lines unless modularized.

## Proposed Decomposition
1. **Tuple Formatting & Result Models (`libs/runefoble_auth/src/runefoble_auth/sync_tuples.py`)**:
   - Extract `SyncResult` schema, role mapping normalization tables, and low-level tuple read/write helper utilities (< 120 lines).
2. **Domain Event Handler (`libs/runefoble_auth/src/runefoble_auth/sync_events.py`)**:
   - Extract `handle_domain_event` implementation with CloudEvent payload parsing and entity dispatch logic (< 140 lines).
3. **Sync Service Coordinator (`libs/runefoble_auth/src/runefoble_auth/sync.py`)**:
   - Retain `ZitadelSpiceDBSyncService` class coordinator, delegating event handling and tuple generation while keeping 100% backward-compatible public methods (< 160 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal library code structure without altering Zanzibar schema (`runefoble.zed`) or public method signatures.
- **Negotiable (N)**: Submodule organization between tuple formatting and entity synchronization can be adapted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) in core platform authentication and authorization infrastructure.
- **Estimable (E)**: Pure refactoring separating event parsing and tuple formatting from the service coordinator.
- **Small (S)**: Scope strictly isolated to `libs/runefoble_auth/src/runefoble_auth/`; all resulting files < 180 lines.
- **Testable (T)**: Existing blackbox and unit auth tests (`tests/test_blackbox_spicedb_zitadel_sync.py`, `tests/test_spicedb_client.py`) verify 100% identical relationship synchronization.

## Acceptance Criteria
1. Re-exports in `sync.py` and `__init__.py` ensure zero breaking changes to `ZitadelSpiceDBSyncService` public APIs.
2. All modified and new files strictly under 200 lines.
3. 100% test pass rate on `uv run pytest tests/test_blackbox_spicedb*.py`.
4. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
