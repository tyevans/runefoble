---
id: '0811'
title: "Voice Signaling Uses the Verified Identity and Role, Never Client Values"
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: voice_agent
target_release: 0.9.0
---

# TASK-0811: Voice Signaling Uses the Verified Identity and Role, Never Client Values

## Status
Refined

## Summary
The voice signaling join handler takes `user_id` and `role` from the client message and stores them, so a peer can claim another user or a DM role in the room.

## Problem Statement
- `services/voice_agent/src/voice_agent/signaling/handlers.py:33-42`: `data.get("user_id", state.user_id)` and `data.get("role", state.role)` replace the admitted identity.
- `.audit/research/services-backend.md` SVC-03.

## Documentation & Architecture Review
- AGENTS.md Hard Invariant 1 (SpiceDB) and DoR 9.
- ADR-0001, ADR-0015. `docs/how-to/verify-identity-in-fastapi-and-websockets.md`, `docs/how-to/define-spicedb-zanzibar-permissions.md`.

## Product & User Story References
None. Security defect.

## Detailed Specification & Implementation Plan
1. The socket identity comes only from the verified principal at admission. Ignore or reject `user_id` in frames.
2. The role comes from SpiceDB (session relation), not from the frame. A frame that asks for another role gets an error frame.
3. Audit the other signaling handlers for client-supplied identity.

## Frontdoor Blackbox Test Plan
- A peer sends a join frame with another user id and role "dm". The room summary shows the verified user and the SpiceDB role.
- A peer without session access cannot join.

## Definition of Done
- The test plan passes, including with a live SpiceDB (`make test-authz-live`).
- `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high (authorization)
- Source audits: research reports in `.audit/research/` (verified by the orchestrator 2026-11-18)
