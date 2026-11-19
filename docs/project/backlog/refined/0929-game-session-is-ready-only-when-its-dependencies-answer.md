---
id: '0929'
title: "game_session Reports Ready Only When It Can Serve Writes"
status: Refined
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0929: game_session Reports Ready Only When It Can Serve Writes

## Status

Refined.

## Summary

Right after a rollout restart, game_session answered `POST /api/v1/campaigns` with 503 while its pod was Ready. The first e2e scenario after a deploy then failed with a gateway 502. A second run passed.

## Problem Statement

- Gateway log on Kind: `Upstream game_session failed with HTTP 503` on the first `POST /api/v1/campaigns` after the restart; later creates answered 201.
- The readiness probe of game_session is `GET /healthz` (check the template); it may report ready before the event store, SpiceDB or Redis answer.

## Documentation & Architecture Review

- `docs/reference/ports-and-endpoints.md` (ingress routing table), `deployments/helm/runefoble/values.yaml` (ingress paths).
- ADR-0005 (Kind and Helm), ADR-0015 (failures are visible).

## Product & User Story References

- `e2e/features/session_lobby_and_vtt.feature` scenarios 3 and 4.

## Detailed Specification & Implementation Plan

1. Find the 503 source on the first write after start-up (event store pool, SpiceDB channel or Redis). Add the missing log line if the 503 is not logged.
2. Make the readiness probe use a check that reflects write readiness (for example `/healthz` reports not ready until the dependencies answered once), without making `/healthz` slow.
3. Apply the same rule to the other services if they share the probe pattern, or file a follow-up.

## Frontdoor Blackbox Test Plan

- Blackbox: with a dependency that is not reachable yet, `/healthz` answers 503 and the write route answers 503 with a log line; when the dependency comes up, `/healthz` answers 200 and the write succeeds.
- Orchestrator on Kind: restart game-session and run `app_shell_routing_state.feature` at once; it passes.

## Definition of Done

- Tests pass. Docs and CHANGELOG `Fixed` entry. The orchestrator runs the named Playwright scenarios on Kind.

## Audit Provenance

- Severity: medium
- Source audits: .audit/work/e2e_full3.log
