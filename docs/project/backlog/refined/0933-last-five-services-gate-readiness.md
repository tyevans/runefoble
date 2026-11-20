---
id: '0933'
title: The Last Five Services Gate Readiness, and a Waiting Deploy Cannot Deadlock
status: Refined
created: 2026-11-19
dependencies:
- '0931'
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds:
- PRD-0025
governing_stories: []
target_bc: core
target_release: 1.0.0
---

# TASK-0933: The Last Five Services Gate Readiness, and a Waiting Deploy Cannot Deadlock

## Status

Refined. Follow-up of TASK-0931 (`.audit/work/0931.md`).

## Summary

rules-compendium, campaign-analytics, voice-agent, inference-worker and gateway-mcp still probe `/healthz`. Also, asset-forge readiness now waits for the Silo asset bucket, and the bucket Job is a post-install/post-upgrade hook. `helm install --wait` waits for pods to be Ready before hooks run, so a fresh install with `--wait` never becomes ready. `make helm-deploy` does not use `--wait` today.

## Problem Statement

- `deployments/helm/runefoble/values.yaml`: five services set the probe path to `/healthz`.
- `.audit/work/0931.md`: the hook order and `--wait` warning.

## Documentation & Architecture Review

- The readiness how-to from TASK-0930. `docs/reference/platform-services.md` (Silo buckets).

## Product & User Story References

None. Deployability.

## Detailed Specification & Implementation Plan

1. Gate `/readyz` for the five services with the shared helper (only the dependencies each uses) and set their probe paths.
2. Remove the deadlock: create the buckets in a form that does not wait for app readiness (for example the bucket Job runs as a normal Job that waits for Silo, not as a post-install hook, or the asset-forge readiness waits for Silo but not the bucket and the upload path reports a missing bucket as a clear 503). Pick one, test it with `helm template`, and document it.
3. Record in `docs/reference/cli-interfaces.md` whether `--wait` is supported.
4. Add a `startupProbe` to every app deployment (default template and values), so that the liveness probe starts only after the service listens. On 2026-11-19 a rollout restart of all 15 services made game-session take more than 35 s to listen. The liveness probe (delay 5 s, 3 failures at 10 s) killed it (exit 137), and the next e2e scenarios got 503 `ConnectError`. Size the startup budget from a measured cold start under a full restart, and state it in the values comments.

## Frontdoor Blackbox Test Plan

- Per service: unreachable dependency gives `/readyz` 503; reachable gives 200.
- Helm template test: every app deployment has a `startupProbe`, and every readiness probe calls `/readyz`; the bucket creation does not depend on hook order after app readiness.
- Orchestrator on Kind: a full deploy and the full e2e suite.

## Definition of Done

- Tests pass. `helm lint` and `helm template` pass. CHANGELOG `Fixed` entry.

## Audit Provenance

- Severity: medium
- Source audits: .audit/work/0931.md
