---
id: '0674'
title: Gateway Health Reports Probed Downstream Status
status: Refined
created: 2026-11-17
dependencies:
- TASK-0580
- TASK-0598
governing_adrs:
- ADR-0005
- ADR-0007
- ADR-0015
governing_prds:
- PRD-0023
governing_stories:
- US-0068
target_release: 0.9.0
---

# TASK-0674: Gateway Health Reports Probed Downstream Status

## Status
Refined. Created from the discovered-defect triage of round 1 (2026-11-17).

## Summary
The gateway health route lists five downstream services as "operational" with no check. An operator reads a healthy status while a service is down. This task replaces the static strings with probed status.

## Problem Statement
- `gateway/api/src/gateway_api/routers/health.py` (lines 14-30) returns `"operational"` for `the_watcher`, `game_session`, `board_state`, `character_sheet`, and `voice_agent`. No request is sent. Only the event bus value is real.
- ADR-0015 item 1 forbids canned payloads in the gateway.

## Documentation & Architecture Review
- TASK-0580 adds a typed service client with timeouts and error mapping. Use it for the probes.
- TASK-0598 defines the gateway route ownership table. The health route is a gateway-local route. Add its mode there.
- `docs/reference/ports-and-endpoints.md` and `docs/reference/platform-services.md`: document the new response fields.

## Product & User Story References
- PRD-0023 and US-0068: the App Shell and operators see which services are running.

## Detailed Specification & Implementation Plan
1. Add a settings-driven list of downstream health URLs. Use the `RUNEFOBLE_<SERVICE>_URL` names from TASK-0624.
2. In the health route, probe every downstream service in parallel with the typed client. Use a short timeout (default 1 second, from settings). Do not cache results.
3. Map each result to one of: `operational` (HTTP 200), `degraded` (other HTTP status), `unreachable` (timeout or connection error).
4. Keep the top-level route status at `healthy` when the gateway process runs. The downstream map shows the probe result. Do not fail the liveness check on a downstream error.
5. Remove the static strings. No default value for a missing URL. A missing URL reports `not_configured`.

## Frontdoor Blackbox Test Plan
- Start the gateway with test doubles at the network boundary for three services (HTTP 200) and one service (HTTP 500). Point the fifth URL to a closed port. `GET /healthz` returns the map: three `operational`, one `degraded`, one `unreachable`.
- Stop one double. The next `GET /healthz` reports that service as `unreachable`.
- Assert only HTTP responses. No private state.

## Definition of Done
- Tests above pass. No literal `"operational"` string remains in `gateway/api/src`.
- Gateway route ownership table (TASK-0598) and ports reference updated.
- Changed files under 500 lines. `uv run pytest` and `make lint` pass.

## Audit Provenance

- Severity: medium
- Source audits: `work/0620.md`
