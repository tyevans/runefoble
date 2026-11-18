---
id: '0579'
title: 'Event Catalogue Alignment: Orphan Producers and Consumers, Wire Types, Board Forge Events'
status: Complete
created: 2026-11-17
dependencies:
- TASK-0565
- TASK-0578
governing_adrs:
- ADR-0006
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0015
- PRD-0005
governing_stories:
- US-0010
- US-0049
- US-0055
target_release: 0.9.0
---

# TASK-0579: Event Catalogue Alignment: Orphan Producers and Consumers, Wire Types, Board Forge Events

## Status
Complete

## Summary
The event catalogue has drifted from the code. Seventeen registered classes have no producer and thirty-eight have no code consumer. About thirty documented topic names do not match any emitted type. Some classes declare a wire type that differs from their class name and print import warnings. Forge events have no consumer, the standee export publishes nothing, and the portrait event goes to the wrong stream. This task decides every orphan event, aligns names with one rule, and wires the forge events that a real flow needs.

## Problem Statement
- 17 classes have no producer, including `CombatRoundAdvanced` (handled in TASK-0574), `TurnStarted`, `ParticipantJoined`, `CriticalHitScored` (these have consumers, so the missing producer breaks flows), `ReactionPromptTriggered`, `ReactionOpportunityResolved`, `SecretTrapTriggered`, `VisibilityMaskUpdated`, `TokenKnockbackApplied`, `ElevationChanged`, `CameraTargetUpdated`, and others (w3-event-wiring F7).
- 38 classes have no code consumer, including `WatcherActionProposed`, `WatcherActionVetoed`, `WatcherActionApproved`, `WatcherActionModified`, and `WorldTickExecuted` (w3-event-wiring F8). Audience events are covered by TASK-0575 and TASK-0441.
- `docs/reference/events-schema.md` lists about 30 `runefoble.events.*` names that no class emits, for example `runefoble.events.lore.document_ingested` and `runefoble.events.compendium.monster_indexed` (w3-event-wiring F11). `runefoble.events.voice.speech_interrupted` does not match `voice.speech.interrupted` (`voice.py:108-116`).
- Stream names are inconsistent: `runefoble:events:world` (`the_watcher/dependencies.py:32`) and `runefoble:events:system` (`gateway_mcp/dynamic/events.py:10`) use colons.
- 132 classes declare an explicit `event_type` that differs from the class name. `MercenaryBounty*` classes print import warnings (`contracts.py:14-60`). `voice.py:108-109` registers one class under two types (w3-event-wiring F12, w1-gates-python F2).
- `services/asset_forge/src/asset_forge/routers/print_forge.py` `export_standees` records `PrintPdfForged` but publishes nothing. `routers/battlemap.py` says the service pushes geometry to `board_state`, but nothing consumes `BattlemapForged` (w2-asset-forge F10). `routers/wardrobe.py` publishes `PortraitVariantGenerated` to the asset stream, and the character service consumes it on a different stream.
- `services/campaign_lore/` `CompendiumAggregate` index events are never emitted by production code (w2-rules-compendium F10).

## Documentation & Architecture Review
- `docs/reference/events-schema.md` is the catalogue. Update it to match the decided set.
- `docs/reference/redis-streams-event-bus.md` must define one naming rule and both stream names.
- `libs/runefoble_events` alias modules are removed by TASK-0487 (refined). Coordinate with it. Do not re-add aliases here.

## Product & User Story References
- [`prd-0015-generative-handouts-relic-inspector-and-printable-forge.md`](../../product/accepted/prd-0015-generative-handouts-relic-inspector-and-printable-forge.md)
- [`us-0049-printable-tabletop-forge-and-stl-tokens.md`](../../user_stories/accepted/us-0049-printable-tabletop-forge-and-stl-tokens.md)
- [`us-0055-dynamic-character-wardrobe-and-condition-portraits.md`](../../user_stories/accepted/us-0055-dynamic-character-wardrobe-and-condition-portraits.md)

## Detailed Specification & Implementation Plan
1. Decision table: for each of the 17 no-producer classes, either add the producer (only where a real flow needs it: `ReactionPromptTriggered`, `ReactionOpportunityResolved`, `SecretTrapTriggered`, `CriticalHitScored`, `TurnStarted`, `ParticipantJoined`) with a frontdoor test, or delete the class and its consumer branches. Record the decision in the catalogue.
2. For each no-consumer class, add a reader with a test, or stop publishing it. Watcher action events get a reader in the watcher's own projection (TASK-0568 owns their aggregate; this task records the reader decision only).
3. One wire-type rule: `runefoble.events.<bc>.<snake_case>` for every class. Remove the duplicate registration in `voice.py`. Remove the warning-producing mismatch. Rename `runefoble:events:world` and `runefoble:events:system` to the dotted form, with a migration note for stream consumers.
4. Forge: add a `board_state` consumer for `BattlemapForged` (or a documented, tested client step that posts `board_geometry_payload` to board_state). `export_standees` publishes `PrintPdfForged` through the publish path with a test. `PortraitVariantGenerated` routes to the character stream, with a test that the wardrobe receives it.
5. Update the catalogue and `redis-streams-event-bus.md`.

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** create a battlemap through the public asset-forge route. Then read the board through its public route. Before: the board has no geometry. After: the geometry is present.
- **Fail before, pass after:** export standees through the public route, then read the asset stream. Before: no `PrintPdfForged` entry. After: one entry.
- **Fail before, pass after:** `pytest -W error::UserWarning` on the events package imports cleanly. Before: three warnings.
- **Fail before, pass after:** a wardrobe variant generated through the public route appears in the character's wardrobe read. Before: absent.
- Public routes and stream reader only.

## Definition of Done
1. Every registered event class has a recorded decision, a producer or deletion, and a consumer or deletion.
2. One topic naming rule applied. Both colon streams renamed. Events-schema and bus reference match the code.
3. Four tests above pass. No import-time event-type warning.
4. `uv run pytest` and `make health-check` pass. Files under 500 lines. Note in the index report if this task must be split during execution.
5. `CHANGELOG.md` entry for each renamed stream and removed event.

## Orchestrator Addenda (2026-11-17, round 2)

Source: `.audit/synth/discovered-round2.md`.

- libs/runefoble_events/src/runefoble_events/watcher_events/narrative.py:41 types tension_level as str. Use the Literal values of the inference worker TensionLevel type.

## Audit Provenance

- Severity: high
- Source audits: `w3-event-wiring.md`, `w2-asset-forge.md`, `w1-gates-python.md`, `w2-rules-compendium.md`
