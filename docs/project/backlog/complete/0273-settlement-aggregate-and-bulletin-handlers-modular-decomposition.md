---
id: '0273'
title: Settlement Aggregate and Bulletin Handlers Modular Decomposition
status: Complete
created: 2026-09-28
dependencies:
- TASK-0259
governing_adrs:
- ADR-0002
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0024
governing_stories:
- US-0072
- US-0076
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/307
---
# TASK-0273: Settlement Aggregate and Bulletin Handlers Modular Decomposition

## Status
Refined

## Summary
Decompose `services/game_session/src/game_session/settlement/settlement_aggregate.py` (455 lines, 91.0% of limit) by extracting bulletin board notice event handlers and mutation commands into a dedicated module `bulletin_handlers.py` and frontier haven legacy chartering logic into `charter_handlers.py`, reducing the core aggregate file to < 160 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/settlement/settlement_aggregate.py` currently embeds 455 lines of Python code, nearing the 500-line invariant limit. It encapsulates core settlement founding and tier scaling, West Marches communal frontier haven chartering, facility tier upgrades, and town bulletin board pinning, removal, and cipher decryption. As additional civic districts, town defenses, and civic projects are introduced, this file will breach Hard Invariant 6 unless decomposed.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/define-event-sourced-aggregates.md`: Declarative aggregate architecture, `@handles` decorators, and event replay.
  - `docs/reference/events-schema.md`: CloudEvents domain schemas for settlement and bulletin events.
- **Governing Architecture & ADRs**:
  - **ADR-0002: Domain Events via eventsource-py**: State transitions flow strictly through `DeclarativeAggregate` subclasses with `@handles` methods.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean aggregate boundaries and single-responsibility event handlers.
  - **ADR-0011: Event Sourcing & Storage Strategy**: Event sourcing persistence and aggregate repository replay.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0024-settlement-haven-builder-and-establishment-ecosystem.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-establishment-ecosystem.md)
  - [`us-0072-settlement-haven-builder-and-establishment-zoning.md`](../../user_stories/accepted/us-0072-settlement-haven-builder-and-establishment-zoning.md)
  - [`us-0076-town-bulletin-board-and-civic-proclamations.md`](../../user_stories/accepted/us-0076-town-bulletin-board-and-civic-proclamations.md)

## Detailed Specification & Implementation Plan
1. **Bulletin Handlers Extraction (`services/game_session/src/game_session/settlement/bulletin_handlers.py`)**:
   - Extract `BulletinNoticePinnedEvent`, `BulletinNoticeRemovedEvent`, and `CipherNoticeDecryptedEvent` handlers and command helper methods (`pin_bulletin_notice`, `remove_bulletin_notice`, `decrypt_cipher_notice`) into a dedicated mixin/handler module (< 140 lines).
2. **Charter & Facility Handlers Extraction (`services/game_session/src/game_session/settlement/charter_handlers.py`)**:
   - Extract legacy frontier `SettlementCharteredEvent`, `SettlementUpgradedEvent`, and `SettlementRestBoonClaimedEvent` handlers and command methods (`charter_haven`, `upgrade_facility`, `claim_rest_boon`) (< 130 lines).
3. **Core Settlement Aggregate Refactoring (`services/game_session/src/game_session/settlement/settlement_aggregate.py`)**:
   - Compose handlers via mixins, keeping `SettlementAggregate` focused on founding, district zoning, and civic tier upgrades (`found`, `upgrade_tier`) (< 160 lines).
4. **Verification**:
   - Run `uv run pytest tests/test_blackbox_settlement_haven_aggregate.py tests/test_blackbox_bulletin_board.py` to ensure complete behavioral parity.

## INVEST Criteria Evaluation
- **Independent (I)**: Internal aggregate decomposition without breaking domain events or public API contracts.
- **Negotiable (N)**: Mixin vs delegate structure can be tuned as long as `@handles` registration works cleanly with `eventsource-py`.
- **Valuable (V)**: Prevents aggregate from breaching the 500-line limit (Hard Invariant 6).
- **Estimable (E)**: Handler and command extraction is straightforward.
- **Small (S)**: Target files will each be under 160 lines.
- **Testable (T)**: Existing blackbox test suites provide immediate regression protection.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `services/game_session/src/game_session/settlement/settlement_aggregate.py` reduced to strictly < 180 lines.
2. Extracted handler modules each strictly < 150 lines per Hard Invariant 6.
3. All existing settlement haven and bulletin board test suites pass without regression.
4. Code passes lint and typecheck (`uv run ruff check .` and `uv run ruff format --check .`).
