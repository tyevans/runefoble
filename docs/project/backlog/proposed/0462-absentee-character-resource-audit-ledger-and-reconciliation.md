---
id: '0462'
title: Absentee Character Resource Audit Ledger and DM Reconciliation API
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0003
- TASK-0055
- TASK-0356
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0002
- PRD-0006
- PRD-0023
governing_stories:
- US-0002
- US-0027
target_release: 0.9.0
---

# TASK-0462: Absentee Character Resource Audit Ledger and DM Reconciliation API

## Status
Proposed

## Summary
Implement an itemized resource audit ledger and one-click DM reconciliation workflow in `services/game_session` and `gateway/api`. Track delta of spell slots used, potions and consumables expended, HP damage sustained, and currency spent while a character is operated by an AI stand-in during a session. Expose Gateway and Game Session REST endpoints enabling returning players (Sarah) to inspect their resource audit ledger upon login, and empowering the DM to approve, adjust, or refund expenditures before applying permanent changes back to the character sheet aggregate.

## Problem Statement
PRD-0002 and US-0027 explicitly mandate: "Resource Audit Ledger: Returns an itemized list of spell slots used, potions consumed, damage taken, and gold spent during stand-in operation" and "DM Reconciliation: The DM can quickly approve or adjust resource expenditures with one click." While TASK-0003 and TASK-0055 provide the stand-in decision engine and tactical guardrails, there is no discrete audit ledger tracking stand-in resource expenditures separately from the player's intentional actions, nor is there a reconciliation mechanism allowing the DM to refund or adjust resources if an AI stand-in behaved unexpectedly or if the group agreed to waive consumable use.

## Governing Architecture & ADRs
- **ADR-0001: Zanzibar Fine-Grained Authorization**: SpiceDB Zanzibar permissions checking `read` on session/character for returning players and `write` on session for DM reconciliation.
- **ADR-0005: Platform Identity & PostgreSQL Persistence**: Persistent storage of ledger entries with relational schema and in-memory read models.
- **ADR-0007: Domain-Driven Design Architecture**: Clean bounded context separation between `game_session`, `character_sheet`, and `gateway/api`.
- **ADR-0011: eventsource-py Core Event Sourcing**: Emit `AbsenteeResourceAuditLedgerGenerated` and `AbsenteeResourceAuditReconciled` domain events.

## Product & User Story References
- [`prd-0002-missing-player-ai-stand-in-with-penalties.md`](../../product/accepted/prd-0002-missing-player-ai-stand-in-with-penalties.md)
- [`us-0002-absent-player-mimicked-by-ai-with-penalties.md`](../../user_stories/accepted/us-0002-absent-player-mimicked-by-ai-with-penalties.md)
- [`us-0027-absentee-character-resource-ledger-and-recap-reel.md`](../../user_stories/accepted/us-0027-absentee-character-resource-ledger-and-recap-reel.md)

## Scope of Work
1. **Resource Audit Ledger Model & State (`services/game_session/src/game_session/absentee/ledger.py`)**:
   - Define `AbsenteeResourceEntry` capturing delta types: `spell_slot`, `consumable_item`, `currency`, `hp_damage`.
   - Record stand-in action context, turn timestamp, and rationale for expenditure.
   - Support reconciliation statuses (`pending`, `approved`, `adjusted`, `refunded`).
2. **REST Endpoints (`services/game_session/src/game_session/absentee/router.py`)**:
   - `GET /api/v1/sessions/{session_id}/absentee/{character_id}/audit-ledger`: Query itemized ledger with net delta summary.
   - `POST /api/v1/sessions/{session_id}/absentee/{character_id}/reconcile`: DM endpoint to approve or adjust specific entries with one-click refund actions.
3. **Gateway Zanzibar Authorization Proxy (`gateway/api/src/gateway_api/routers/absentee_ledger.py`)**:
   - Expose Gateway routes `/api/v1/sessions/{session_id}/absentee/{character_id}/audit-ledger` and `/api/v1/sessions/{session_id}/absentee/{character_id}/reconcile`.
   - Validate SpiceDB Zanzibar authorization (`read` for character owner/party, `manage` / `write` for session DM).
4. **Domain Event Sourcing (`libs/runefoble_events/src/runefoble_events/absentee.py`)**:
   - Register `AbsenteeResourceAuditLedgerGenerated` and `AbsenteeResourceAuditReconciled` CloudEvents.

## Definition of Done
1. `ledger.py`, `router.py`, and `absentee_ledger.py` implemented strictly < 200 lines each per Hard Invariant 6.
2. SpiceDB Zanzibar permission checks enforced on Gateway proxy endpoints.
3. One-click reconciliation adjustments accurately update ledger statuses and emit domain events.
4. Unit and blackbox tests verify ledger generation, itemized entries, and DM adjustments.
