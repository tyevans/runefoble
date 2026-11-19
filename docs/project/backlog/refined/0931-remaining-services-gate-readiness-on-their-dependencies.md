---
id: '0931'
title: The Remaining Services Gate Readiness on Their Dependencies
status: Refined
created: 2026-11-19
dependencies:
- '0930'
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---

# TASK-0931: The Remaining Services Gate Readiness on Their Dependencies

## Status

Refined. Follow-up of TASK-0930 (`.audit/work/0930.md`).

## Summary

TASK-0930 added the shared readiness checks and gave every app pod a readiness probe. game_session and gateway-api serve a gated `/readyz`. Ten services still probe `/healthz`, which reports ready before their dependencies answer.

## Problem Statement

- No gated `/readyz` yet: the-watcher, board-state, character-sheet, campaign-lore, rules-compendium, asset-forge, soundscape, campaign-analytics, inference-worker and gateway-mcp (and voice-agent, which probes `/healthz`).
- `deployments/helm/runefoble/values.yaml`: these services set the probe path to `/healthz`.

## Documentation & Architecture Review

- The shared readiness helper and how-to from TASK-0930.

## Product & User Story References

None. Deployability.

## Detailed Specification & Implementation Plan

1. Each listed service registers its dependency checks with the shared helper (event store, SpiceDB, Redis, Silo, or upstream owners, only the ones it uses) and serves `/readyz`.
2. Set each probe path to `/readyz` and remove the per-service `/healthz` override.
3. Split into two passes of five services if one pass passes about 15 files.

## Frontdoor Blackbox Test Plan

- Per service: an unreachable dependency gives `/readyz` 503 naming it; reachable gives 200.
- Helm template test: every app probe calls `/readyz`.
- Orchestrator on Kind: restart all app deployments and run the full e2e suite at once.

## Definition of Done

- Tests pass. `helm lint` and `helm template` pass. CHANGELOG `Fixed` entry.

## Audit Provenance

- Severity: medium
- Source audits: .audit/work/0930.md
