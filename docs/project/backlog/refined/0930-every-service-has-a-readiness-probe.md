---
id: '0930'
title: Every Service Has a Readiness Probe That Reflects Its Dependencies
status: Refined
created: 2026-11-19
dependencies:
- '0929'
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---

# TASK-0930: Every Service Has a Readiness Probe That Reflects Its Dependencies

## Status

Refined. Follow-up of TASK-0929 (`.audit/work/0929.md`).

## Summary

TASK-0929 gave game_session a `GET /readyz` that answers 503 until its event store, SpiceDB and Redis each answered once, and a Helm readiness probe that calls it. Only `voice-agent` and `audience-studio` had a readiness probe before. The other services show Ready as soon as the process starts, so the first requests after a rollout can fail.

## Problem Statement

- `deployments/helm/runefoble/templates/`: no `readinessProbe` for gateway-api, the-watcher, board-state, character-sheet, campaign-lore, rules-compendium, asset-forge, soundscape, campaign-analytics, gateway-mcp and inference-worker (see the list in `.audit/work/0929.md`).
- TASK-0929 wrote the readiness logic in game_session only.

## Documentation & Architecture Review

- `docs/how-to/run-supervised-redis-stream-consumers.md` (`/healthz` status), the new game_session `/readyz` (TASK-0929).

## Product & User Story References

None. Deployability.

## Detailed Specification & Implementation Plan

1. Move the readiness logic of TASK-0929 into `libs/runefoble_platform` as one helper: each service registers its dependency checks (event store, SpiceDB, Redis, Silo, upstream owners as needed), and the helper serves `GET /readyz`. game_session uses the helper (no copy left).
2. Each service registers only the dependencies it uses. `/readyz` stays fast (cached result after the first success, a short timeout per check).
3. The chart gives every app deployment a `readinessProbe` on `/readyz` (one shared template helper, values-driven).
4. Write `docs/how-to/add-a-readiness-check.md` (generic pattern, AGENTS.md rule) and update `docs/reference/ports-and-endpoints.md`.

## Frontdoor Blackbox Test Plan

- Per service: with a dependency that is not reachable, `/readyz` answers 503 and names it; when it is reachable, 200.
- Helm template test: every app deployment has a readiness probe on `/readyz`.
- Orchestrator on Kind: restart all app deployments and run the full e2e suite at once; no scenario fails with a 502 or 503 at start-up.

## Definition of Done

- Tests above pass. `helm lint` and `helm template` pass. How-to written. CHANGELOG `Fixed` entry.

## Audit Provenance

- Severity: medium
- Source audits: .audit/work/0929.md
