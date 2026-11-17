---
id: '0622'
title: Helm Deployment, Service, and Swagger Entry for the Inference Worker
status: Refined
created: 2026-11-17
dependencies:
- TASK-0620
governing_adrs:
- ADR-0005
- ADR-0006
governing_prds:
- PRD-0001
governing_stories:
- US-0007
target_release: 0.9.0
severity: high
source_audits:
- w2-inference-worker.md
- w1-gates-infra.md
- w1-the-watcher.md
- w3-event-wiring.md
---

# TASK-0622: Helm Deployment, Service, and Swagger Entry for the Inference Worker

## Status
Refined

## Summary
`services/inference_worker` serves HTTP on port 8100 (`/inference/v1/*`, `/healthz`) but has no Helm Deployment, Service, image, or Swagger URL. Hard Invariant 5 requires `/openapi.json` and a Swagger registration for every HTTP service. Deploy it in the chart and register it with the Swagger hub.

## Problem Statement
- `grep -c inference deployments/helm/runefoble/values.yaml` returns 0 (`w2-inference-worker.md` F3).
- `services/inference_worker/src/inference_worker/config.py:20` defaults `port` to 8100; `api.py` serves `/healthz`.
- `the_watcher` never calls the worker in the cluster, so speech, narration and stand-in paths always use the local heuristic engine (`w1-the-watcher.md` F2, `w3-event-wiring.md` F14).
- Its input stream `runefoble.inference.requests` has no producer; this task deploys the HTTP path only.

## Documentation & Architecture Review
- `docs/reference/ports-and-endpoints.md` and `docs/reference/platform-services.md` have no inference entry (`w2-inference-worker.md` F9). Add the port and routes in this task.
- ADR-0005: service templates follow `templates/services.yaml` and `soundscape.yaml` patterns.
- ADR-0006: keep the Redis consumer off in the chart (`RUNEFOBLE_WORKER_REDIS_ENABLED` stays false) until a producer exists.
- PRD-0001 governs The Watcher inference path.

## Product & User Story References
- PRD-0001, US-0007 (autonomous DM execution) in `docs/project/product/accepted/` and `docs/project/user_stories/accepted/`.

## Detailed Specification & Implementation Plan
1. Add `services.inferenceWorker` to `values.yaml`: image `runefoble/inference-worker:0.1.0`, replicas 1, port 8100, `backend: mock` default, and a `openaiCompatibleBaseUrl` value left empty.
2. Add a Deployment and ClusterIP Service `inference-worker` in `templates/` (new file `inference-worker.yaml`), port from values. Env: `RUNEFOBLE_WORKER_HOST=0.0.0.0`, `RUNEFOBLE_WORKER_PORT`, backend and base URL from values, no secret literals.
3. Add `http://inference-worker:8100/openapi.json` ("Inference Worker Service") to `swaggerUI.urls`.
4. Add `inference-worker` to the `IMAGE_TABLE` in the Makefile (TASK-0620), port 8100.
5. Add the worker port and the `/inference/v1/*`, `/healthz` routes to the two reference docs.
6. Do not add `RUNEFOBLE_INFERENCE_URL` to the-watcher here; that is TASK-0624.

## Frontdoor Blackbox Test Plan
- Before fix: `helm template` output contains no `inference-worker` Service; `values.yaml` Swagger list has no entry.
- After fix: `helm template deployments/helm/runefoble | grep -A3 'name: inference-worker'` shows Service port 8100. A pytest test renders the chart and asserts a Service named `inference-worker` with port 8100 and a Swagger URL for it. Through the cluster: `GET http://localhost/swagger-ui` lists the worker (manual gate).
- `GET /inference/v1/health` (or `/healthz`) through the Service returns 200 in the built image.

## Definition of Done
1. Helm lint and template pass; the rendered chart includes the Deployment, Service and Swagger URL.
2. Swagger hub lists 13 entries (12 HTTP services plus gateway).
3. Docs list port 8100 and the routes.
4. The image builds through `make images`.
5. No file above 500 lines.
