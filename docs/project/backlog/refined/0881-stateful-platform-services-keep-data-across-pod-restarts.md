---
id: '0881'
title: Stateful Platform Services Keep Their Data Across Pod Restarts
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0005
- ADR-0011
governing_prds:
- PRD-0023
governing_stories:
- US-0065
target_release: 0.9.0
---

# TASK-0881: Stateful Platform Services Keep Their Data Across Pod Restarts

## Status
Refined

Found by the orchestrator on 2026-11-18 during a Kind redeploy.

## Summary
`deployments/helm/runefoble/templates/postgres.yaml` runs PostgreSQL as a Deployment with no data volume. Its only volume is the init script ConfigMap. The cluster has no PersistentVolumeClaim. Any restart of the PostgreSQL pod (a rollout, a node restart, an eviction) deletes every event store, the Zitadel database and the SpiceDB datastore. Event sourcing (ADR-0011) needs durable storage. Check Silo and Redis for the same problem.

## Documentation & Architecture Review
- ADR-0005 (Kubernetes and Helm), ADR-0011 (event sourcing).
- `docs/reference/platform-services.md`, `docs/tutorials/01-local-development-setup.md`.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)

## Detailed Specification & Implementation Plan
1. Run PostgreSQL as a StatefulSet with a `volumeClaimTemplates` entry for `/var/lib/postgresql/data`. The size and the storage class come from `values.yaml` (`postgres.persistence.size`, `postgres.persistence.storageClass`; Kind's default class is `standard`).
2. Do the same for Silo object data. Decide for Redis: the streams carry the outbox and consumer state, so persist them (AOF on a volume) or record why not.
3. Update the platform services reference and the local setup tutorial (a cluster delete removes the volumes).

## Frontdoor Test Plan
- `helm template` renders a StatefulSet with a volume claim for PostgreSQL and Silo (a chart render test).
- On Kind: create a campaign through the gateway, delete the PostgreSQL pod, wait for it to come back, and read the campaign again (manual check recorded in the task report; the orchestrator runs it).

## INVEST Criteria Evaluation
Small: chart templates and values. Testable through the chart render and one cluster check.

## Definition of Done
1. Data survives a PostgreSQL pod restart on Kind. 2. `helm lint` and `make helm-template` pass. 3. Docs updated. 4. `make health-check` passes.
