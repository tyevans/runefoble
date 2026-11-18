---
id: '0702'
title: Voice Room Coordinator Saves Its Room Aggregate
status: Refined
created: 2026-11-17
dependencies:
- TASK-0561
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: voice_agent
target_release: 0.9.0
---
# TASK-0702: Voice Room Coordinator Saves Its Room Aggregate

## Status
Refined. Found by the TASK-0561 worker and checked by the orchestrator.

## Summary
`VoiceRoomCoordinator` never calls `repository.save`. Rooms live only in an in-process dict, so a restart or a second replica loses every room. This breaks Hard Invariant 2.

## Problem Statement
- `services/voice_agent/src/voice_agent/coordinator.py`: commands (`peer_joined`, `peer_left`, `mute_toggled`, `apply_vocal_preset`, `toggle_voice_filter`, `kick_peer`) change the aggregate and publish events, but do not save.
- `get_or_load_room` keeps the aggregate in `self._aggregates` for the life of the process.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011, ADR-0015.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Save the aggregate after each command, before the event publish (publish policy from TASK-0693).
2. Remove the long-lived `_aggregates` cache, or make it a read-through cache that cannot serve stale state across replicas. Prefer removal.
3. Use the TASK-0561 load helpers: not found starts a new room; a store error gives 503.
4. Keep telemetry (non-domain, best effort) out of the aggregate.

## Frontdoor Blackbox Test Plan
- Join a peer through the public voice route. Build a new coordinator over the same event store (or restart the service in a subprocess, see TASK-0698). Read the room summary. Assert the peer is present.
- Store outage during join: assert 503 and no published join event.

## Definition of Done
- Every coordinator command saves the aggregate.
- No in-process room cache keeps domain state.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high
- Source audits: `work/0561.md`
