---
id: '0882'
title: Inference Responses Drop the Always-False degraded Field
status: Complete
created: 2026-11-18
dependencies:
- TASK-0740
- TASK-0838
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0001
governing_stories:
- US-0031
target_release: 0.9.0
---

# TASK-0882: Inference Responses Drop the Always-False degraded Field

## Status
Complete

Source: TASK-0740 report (`.audit/work/0740.md`).

## Summary
TASK-0740 removed every fallback path from the inference worker. The `degraded` field of the intent, narration and stand-in responses is now always `false`. A field that can never change is dead contract (DoR 9). Remove it from the worker responses, The Watcher response models, every consumer (TASK-0838 reads it to decide on `narration_unavailable`; a worker failure is now an HTTP error), the UI types, and `docs/reference/inference-worker-response-contract.md`.

## Product & User Story References
- [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)

## Detailed Specification & Implementation Plan
1. `git grep -n degraded` across services, gateway, libs, frontend, services/*/ui, e2e, tests and docs. Remove each use.
2. Where a consumer branched on `degraded`, it branches on the HTTP error instead.

## Frontdoor Test Plan
The worker responses have no `degraded` key. A worker 503 still gives The Watcher's typed failure (for example the `narration_unavailable` whisper).

## INVEST Criteria Evaluation
Small. Testable through the worker and Watcher routes.

## Definition of Done
1. No `degraded` field remains. 2. Tests pass. 3. `make health-check` passes.
