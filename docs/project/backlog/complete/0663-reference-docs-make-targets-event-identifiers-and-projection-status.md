---
id: '0663'
title: Reference Docs List Every Make Target and Real Event Types and State Projection Status Honestly
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0006
- ADR-0011
- ADR-0003
governing_prds: []
governing_stories: []
target_release: 0.9.0
severity: medium
source_audits:
- w3-docs-integrity.md
---

# TASK-0663: Reference Docs List Every Make Target and Real Event Types and State Projection Status Honestly

## Status
Complete

## Summary
Three reference pages disagree with the code they describe. `cli-interfaces.md` omits twelve Make targets. `events-schema.md` lists 23 dotted `runefoble.events.*` identifiers that the code never emits (it emits class names). `redis-streams-event-bus.md` describes projection workers as active, but the presence and session-read projections are in-memory and never instantiated. Generate the event identifier list from code, add the Make target rows, and state the real projection status.

## Problem Statement
- C1 (medium, `docs/reference/cli-interfaces.md`): twelve targets are missing from the table: `seed-admin`, `invite-admin`, `install-tools`, `deploy-remote-worker`, `test-entrypoints`, `test-property`, `test-mutation`, `test-bdd`, `test-e2e`, `test-e2e-ui`, `lint-fix`, and `pre-commit`.
- C3 (low): `make docs-serve` is said to use port 8000. The port is not verified.
- E1 (medium, `docs/reference/events-schema.md`): 23 dotted identifiers have no literal match in code. Examples: `codex.entry_published` (line 967), `west_marches.caravan_ambushed` (line 1070), `game_session.mercenary_bounty_posted` (line 1103), and `system.dynamic_tool_registered` (line 1109). The code's `event_type` values are class names, for example `CodexEntryPublished` (`libs/runefoble_events/src/runefoble_events/lore.py:264`). All 140 cited class names exist.
- E2 (medium): the events reference has drift in several sections (CharacterSheet events, payload drift, canonical rules events that are never emitted, and missing streams). Each section is updated after the matching code fix, so this task only lists the drift and links the owning audit items.
- R2 (medium, `docs/reference/redis-streams-event-bus.md:45-50`): projection workers are described as subscribing to session streams. `PresenceProjection` and `SessionReadProjection` are in memory and not instantiated (`w1-game-session` F10). Describe the current state.

## Documentation & Architecture Review
- ADR-0011: projections are read models over the event store. Their status must match what runs.
- ADR-0006: the Redis Streams topic names are part of the reference. Use the names the code publishes.
- `docs/reference/events-schema.md` is the contract for event payloads. The identifier column must come from the code, not from memory.

## Product & User Story References
Reference documentation. Not user-facing.

## Detailed Specification & Implementation Plan
1. Add a generator script (`scripts/generate_event_catalogue.py`, run with `uv run`) that reads every `event_type` and class-level `event_type` value from `libs/runefoble_events` and writes the identifier list to a data file. The reference page includes that list. A test fails when the page and the generated list differ.
2. Replace the 23 dotted identifiers with the real `event_type` values, or with the class name where no explicit type exists. State which is which.
3. Add the twelve Make target rows to `cli-interfaces.md`. Each row names the target's purpose and its command, read from the Makefile.
4. Verify the `docs-serve` port by running the target locally (or reading the Zensical default in its config) and state the verified port.
5. Rewrite the projection paragraph to: which projections exist, which run in production, and which are in-memory only. Link to the event-store task.
6. Update the E2 drift list with links to the owning audit findings.
7. Keep each file under 500 lines. Split the generated list into its own file.

## Frontdoor Blackbox Test Plan
- `tests/test_blackbox_event_catalogue_doc.py` runs the generator and asserts that every `event_type` cited in `events-schema.md` exists in the generated list and that every Make target in `cli-interfaces.md` exists in the Makefile. Before the change it FAILS on the 23 identifiers and the twelve missing targets. After the change it PASSES.
- The test uses only repository files, no network.

## Definition of Done
1. `cli-interfaces.md` lists every Make target in the Makefile.
2. The events reference cites only real `event_type` values, produced by the generator.
3. The projection paragraph matches the running code.
4. The docs-serve port is verified and stated.
5. The catalogue test passes in `uv run pytest`.
6. Files stay under 500 lines.

## Orchestrator Addenda (2026-11-17)

Source: `.audit/synth/discovered-round1.md`.

- `docs/reference/events-schema.md` lists `(alias: ...)` names (for example lines 67, 120, 129, 135). Remove them with the code aliases in TASK-0487.
