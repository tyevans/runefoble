---
id: '0813'
title: "A SpiceDB Outage Maps to One 503 Answer in Every Service"
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: runefoble_auth
target_release: 0.9.0
---

# TASK-0813: A SpiceDB Outage Maps to One 503 Answer in Every Service

## Status
Complete

## Summary
Services answer a SpiceDB outage in different ways. game_session has no handler, so an outage gives the framework default. asset_forge maps schema defects to 503. the_watcher keeps a copy of the lib handler. Four response bodies exist.

## Problem Statement
- `.audit/research/services-backend.md` SVC-01; `.audit/research/libs.md` F5.
- Lib handler: `libs/runefoble_auth/src/runefoble_auth/authz_http.py:47-48`. Copy: `services/the_watcher/src/the_watcher/authz_errors.py` (removed).

## Documentation & Architecture Review
- AGENTS.md Hard Invariant 1 (SpiceDB) and DoR 9.
- ADR-0001, ADR-0015. `docs/how-to/verify-identity-in-fastapi-and-websockets.md`, `docs/how-to/define-spicedb-zanzibar-permissions.md`.

## Product & User Story References
None. Security defect.

## Detailed Specification & Implementation Plan
1. Every service installs the lib handler, and no service keeps a copy. One body: `{"error": "authorization_unavailable"}` with 503.
2. A schema defect (unknown permission) is a 500 and is logged, not a 503.

## Frontdoor Blackbox Test Plan
- For each service, a test with an unreachable SpiceDB gets 503 with the one body on a permission-checked route.

## Definition of Done
- The test plan passes, including with a live SpiceDB (`make test-authz-live`).
- `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high (authorization)
- Source audits: research reports in `.audit/research/` (verified by the orchestrator 2026-11-18)
