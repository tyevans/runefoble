---
id: '0465'
title: Absentee Resource Audit and Catch-Up Reel Blackbox Test Suite
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0462
- TASK-0463
- TASK-0464
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0005
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0002
governing_stories:
- US-0027
- US-0028
target_release: 0.9.0
---

# TASK-0465: Absentee Resource Audit and Catch-Up Reel Blackbox Test Suite

## Status
Proposed

## Summary
Implement a comprehensive frontdoor blackbox test suite (`tests/test_blackbox_absentee_resource_audit_and_catchup.py` and `frontend/test/absentee-catchup-reel.test.ts`) validating end-to-end absentee workflows: stand-in resource expenditure tracking, Gateway audit ledger queries, SpiceDB Zanzibar DM reconciliation, Catch-Up Reel slide rendering, and affliction voice podcast export.

## Problem Statement
Ensures zero regressions and verifies full compliance with Hard Invariants (Rule 1 Zanzibar checks, Rule 6 file length limit <500 lines, Rule 7 blackbox TDD with frontdoor setup) across all new absentee capabilities introduced by PRD-0002, US-0027, and US-0028.

## Governing Architecture & ADRs
- **ADR-0001: Zanzibar Fine-Grained Authorization**: Verify SpiceDB authorization policies prevent unauthorized players from altering reconciliation records.
- **ADR-0002: Real-Time Audio Streaming and STT/TTS**: Assert absentee podcast reel generation and endpoint streaming.
- **ADR-0005: Platform Identity & PostgreSQL Persistence**: Validate persistent ledger queries across session lifecycles.
- **ADR-0007: Domain-Driven Design Architecture**: Blackbox validation through Gateway frontdoor without reaching into internal service databases.
- **ADR-0011: eventsource-py Core Event Sourcing**: Verify emitted CloudEvents payloads adhere to event schema.

## Product & User Story References
- [`prd-0002-missing-player-ai-stand-in-with-penalties.md`](../../product/accepted/prd-0002-missing-player-ai-stand-in-with-penalties.md)
- [`us-0027-absentee-character-resource-ledger-and-recap-reel.md`](../../user_stories/accepted/us-0027-absentee-character-resource-ledger-and-recap-reel.md)
- [`us-0028-personalized-voice-cloned-stand-in-dialogue.md`](../../user_stories/accepted/us-0028-personalized-voice-cloned-stand-in-dialogue.md)

## Scope of Work
1. **Backend Integration Blackbox Suite (`tests/test_blackbox_absentee_resource_audit_and_catchup.py`)**:
   - Stand-in character simulated across combat turns consuming spell slots and potions.
   - Returning player authenticates with Zitadel JWT and queries `/api/v1/sessions/{session_id}/absentee/{character_id}/audit-ledger`.
   - Verify 403 Forbidden when unauthorized user attempts to view or reconcile another character's ledger.
   - DM authenticates and posts adjustments to `/api/v1/sessions/{session_id}/absentee/{character_id}/reconcile`, asserting ledger state updates to `approved` / `adjusted`.
   - Call `/api/v1/voice/standin/podcast` and assert MP3 metadata payload returned with 200 OK.
2. **Frontend Blackbox Test Suite (`frontend/test/absentee-catchup-reel.test.ts`)**:
   - Mount `runefoble-absentee-catchup-reel` in JSDOM/HappyDOM environment.
   - Assert all 4 carousel slides render expected data (welcome, combat highlights, narrative antics, resource ledger).
   - Assert keyboard arrow navigation and dismiss event emission.

## Definition of Done
1. Both test files stay strictly < 300 lines each per Hard Invariant 6.
2. 100% blackbox interaction via public HTTP routes and Web Component interfaces.
3. Tests pass with zero regressions via `uv run pytest tests/test_blackbox_absentee_resource_audit_and_catchup.py`.
4. Frontend tests pass via `pnpm test` / `npm test`.
