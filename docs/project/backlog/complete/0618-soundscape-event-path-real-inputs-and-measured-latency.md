---
id: '0618'
title: Soundscape Event Path Derives Tension Inputs From Game State and Measures Leitmotif Latency
status: Complete
created: 2026-11-17
dependencies:
- TASK-0438
governing_adrs:
- ADR-0006
- ADR-0014
governing_prds:
- PRD-0010
governing_stories:
- US-0039
- US-0046
target_release: 0.9.0
---

# TASK-0618: Soundscape Event Path Derives Tension Inputs From Game State and Measures Leitmotif Latency

## Status
Complete

## Summary
The soundscape event handlers feed tension scoring with constants: `enemy_cr_balance=2.0` and `2.5`, and a party health ratio that is never passed (always 1.0). The leitmotif response reports a fixed `scheduled_latency_ms=45` as if it were measured. This task derives the inputs from encounter and health events and removes the fixed latency claim.

## Problem Statement
- `services/soundscape/src/soundscape/event_handlers.py:65`: `enemy_cr_balance=2.0` at combat start. Line 68 repeats it in `record_tension_update`. Line 78: `2.5` on round advance.
- `lowest_party_health_ratio` is never passed on the event path. It defaults to 1.0 in `handlers/tension.py`.
- `CharacterHealthChanged` only starts a leitmotif (`event_handlers.py` near line 150).
- `src/soundscape/leitmotif.py:175` and `:275`: `scheduled_latency_ms = 45` with comment "Guaranteed sub-250ms scheduling". No clock measures it.

Sources: `.audit/reports/w2-soundscape.md` F2 and F13.

## Documentation & Architecture Review
- `docs/how-to/manage-dynamic-soundscapes-and-audio-ducking.md`: describes tension inputs and latency. Update it.
- TASK-0438 (refined) subscribes the tactile board handlers. This task depends on it because it edits the same handler module.
- ADR-0006: event payloads must carry the inputs. Update `docs/reference/events-schema.md` for any new field.

## Product & User Story References
- `docs/project/product/accepted/prd-0010-adaptive-soundscape-foley-and-tension-scoring.md`
- `docs/project/user_stories/accepted/us-0039-encounter-tension-adaptive-scoring-and-foley.md`
- `docs/project/user_stories/accepted/us-0046-character-musical-leitmotifs-and-dynamic-themes.md`

## Detailed Specification & Implementation Plan
1. Combat start and round advance events carry the encounter roster balance (or the CR inputs the scoring needs). The handler reads them from the payload. Remove literals.
2. `CharacterHealthChanged` updates the stored lowest party health ratio for the session, and the next tension update uses it.
3. Remove `scheduled_latency_ms`, or set it to a value measured between trigger and playback start on the client. Prefer removal from the API response.
4. Update event schema docs for new payload fields.

## Frontdoor Blackbox Test Plan
- Before fix: publish a combat-start event with a 2-player party at 10% HP, then read the tension route. Tension equals the constant-input value (test fails when it does not reflect the party health).
- After fix: tension increases when health ratio is lowered through a `CharacterHealthChanged` event published on the stream.
- After fix: leitmotif response has no `scheduled_latency_ms` field with a constant value.

## Definition of Done
1. No literal `enemy_cr_balance=` values or `scheduled_latency_ms=45` in `services/soundscape/src`.
2. Files under 500 lines.
3. Blackbox tests pass. `uv run pytest services/soundscape` passes.
4. Ruff check and format pass.
5. Events schema and soundscape how-to updated. `CHANGELOG.md` `[Unreleased]` entry added.

## Audit Provenance

- Severity: medium
- Source audits: `w2-soundscape.md`
