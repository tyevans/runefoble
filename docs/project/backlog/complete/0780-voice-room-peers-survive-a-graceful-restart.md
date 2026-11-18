---
id: '0780'
title: Voice Room Peers Survive a Graceful Restart
status: Complete
created: 2026-11-17
dependencies:
- TASK-0698
governing_adrs:
- ADR-0011
- ADR-0005
governing_prds: []
governing_stories: []
target_bc: voice_agent
target_release: 0.9.0
---

# TASK-0780: Voice Room Peers Survive a Graceful Restart

## Status
Complete

## Summary
When voice_agent shuts down gracefully (SIGTERM, a rolling deploy), it closes each peer socket. The close handler then records `peer_left` with reason `disconnected`. The restored room is empty after the restart, so every client must rejoin.

## Problem Statement
- `services/voice_agent/src/voice_agent/signaling/endpoint.py:91` and `handlers.py:163`: a close during shutdown records `peer_left`.
- TASK-0698 restart tests run voice_agent in a child process; they show the behaviour.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011, ADR-0005.
- `docs/how-to/handle-neural-voice-duplex-and-speech-interruption.md` and the voice room reference.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. During shutdown, close peer sockets with a restart close code (for example 1012, service restart) and do not record `peer_left` for them.
2. On reconnect after a restart, a peer that is still in the room resumes its seat.
3. Document the restart behaviour.

## Frontdoor Blackbox Test Plan
- In a child-process voice_agent: join two peers, send SIGTERM, start the service again: the room still lists both peers, and each client gets close code 1012.

## Definition of Done
- A graceful restart keeps the room membership.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `.audit/work/0698.md` (Discovered)
