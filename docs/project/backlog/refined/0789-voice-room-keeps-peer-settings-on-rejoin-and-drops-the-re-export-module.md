---
id: '0789'
title: Voice Room Keeps Peer Settings on Rejoin and Drops the Re-Export Module
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0011
governing_prds: []
governing_stories: []
target_bc: voice_agent
target_release: 0.9.0
---

# TASK-0789: Voice Room Keeps Peer Settings on Rejoin and Drops the Re-Export Module

## Status
Refined. Found during batch 23 integration, 2026-11-17.

## Summary
A peer that rejoins with the same peer id loses its mute state and vocal preset. `room.py` says it re-exports names for backward compatibility, which DoR 9 forbids.

## Problem Statement
- `services/voice_agent/src/voice_agent/room_aggregate.py` `_on_peer_joined`: resets `is_muted` and the vocal preset fields for an existing peer.
- `services/voice_agent/src/voice_agent/room.py:1`: re-export module.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. A rejoin keeps the existing peer settings.
2. Delete the re-export module and import from the owning modules at every call site.

## Frontdoor Blackbox Test Plan
- Mute a peer, rejoin with the same peer id over the WebSocket, and read the room: the peer is still muted with the same preset.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `.audit/work/0780.md` (Discovered)
