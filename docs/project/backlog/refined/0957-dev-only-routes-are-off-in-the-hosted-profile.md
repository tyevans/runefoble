---
id: '0957'
title: Development-Only Public Routes Are Off in the Hosted Profile
status: Refined
created: 2026-11-19
dependencies:
- '0955'
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds:
- PRD-0025
governing_stories: []
target_bc: core
target_release: 1.0.0
---

# TASK-0957: Development-Only Public Routes Are Off in the Hosted Profile

## Status

Refined. Release One hosting slice 3 (PRD-0025, outcome 4: turns off Mailpit, `/mail`, `/docs` and `/analytics`).

## Summary

The hosted profile removes the public routes and the workloads for Mailpit, Swagger UI and OpenPanel. The guard (0955) rejects any hosted route to a disabled workload. Analytics needs a decision first (input D6).

## Problem Statement

- `deployments/helm/runefoble/values.yaml:44-63` (first host) and `values.yaml:88-107` (second host) route `/docs`, `/swagger-ui`, `/analytics`, `/mail` and `/mailpit` to the development services.
- `deployments/helm/runefoble/values.yaml:248` sets `mailpit.enabled: true`. `templates/mailpit.yaml:1` renders only when it is true.
- `templates/swagger-ui.yaml:1` and `templates/openpanel.yaml:1` have the same switch (`swaggerUI.enabled` at `values.yaml:270`, `openpanel.enabled` at `values.yaml:242`).
- `templates/mailpit.yaml:29-32` accepts any SMTP login (`MP_SMTP_AUTH_ACCEPT_ANY`, `MP_SMTP_AUTH_ALLOW_INSECURE`). It must never run in a public cluster.
- `gateway/api/src/gateway_api/main.py:76-78` sets `docs_url`, `redoc_url` and `openapi_url` on the gateway. These pages are served only if an ingress path routes to them. Removing the ingress paths hides them from the public, and the service still serves `/openapi.json` in the cluster (Hard Invariant 5).
- `templates/zitadel.yaml:131` renders the Zitadel SMTP block only when `mailpit.enabled` is true. Turning Mailpit off also turns off all SMTP for Zitadel until record 0958 adds real SMTP.

## Documentation & Architecture Review

- AGENTS.md, Hard Invariant 5 (services publish `/openapi.json`). Hiding the Swagger UI route keeps this invariant.
- ADR-0015 (b) and (f): no fallback. A removed route returns 404. No substitute page.
- `docs/how-to/test-email-signups-with-mailpit.md`: the development mail flow. Mark it as development only. Add a line that the hosted profile has no Mailpit.
- `docs/reference/platform-services.md`: lists Mailpit and OpenPanel. Mark the hosted state.

## Product & User Story References

- PRD-0025, Checkable Outcome 4 (turn off Mailpit, `/mail`, `/docs` and `/analytics`).
- PRD-0025, "What this does not do": no public sign-up and no abuse controls. Routes stay closed.

## Detailed Specification & Implementation Plan

1. In the hosted example (0955), the `ingress.hosts` list holds only:
   - `/api` to `gateway-api:8000`;
   - `/ws/boards` to `board-state:8002`;
   - `/ws` to `gateway-api:8000`;
   - `/` to `frontend:80`.
   The `/healthz` path on the ingress stays only if the operator needs it for an external probe. Decide in the runbook (0965).
2. Set `mailpit.enabled: false` and `swaggerUI.enabled: false` in the hosted example.
3. Set `openpanel.enabled: false` in the hosted example unless input D6 keeps analytics. If analytics stays, route only the OpenPanel UI behind authentication. This record does not add authentication. Do not expose the OpenPanel UI without it.
4. Analytics check before turning OpenPanel off: find the code that sends analytics events. Confirm that a failed send does not block a player action. If a failed send blocks an action, the record stops and the user decides (ADR-0015 (b)). Do not replace the send with a stub.
5. Extend the guard (0955) with one check. For every ingress path, the target service must be a workload that renders. Map `mailpit` to `mailpit.enabled`, `swagger-ui` to `swaggerUI.enabled`, and `openpanel` to `openpanel.enabled`. The render fails when a path points to a disabled workload.

### Inputs (user decisions)

- D6: whether `/analytics` (OpenPanel) is public, and whether analytics is on at all. Default in this record: off.

## Frontdoor Blackbox Test Plan

New file: `tests/test_blackbox_helm_hosted_routes.py`. It reads rendered manifests only.

- Hosted render: no Ingress path has the prefix `/mail`, `/mailpit`, `/docs`, `/swagger-ui`, or `/analytics`. No Deployment or Service is named `mailpit`, `swagger-ui`, or `openpanel`.
- Hosted render: no Ingress path targets `mailpit`, `swagger-ui`, or `openpanel`.
- Guard: a hosted copy with `mailpit.enabled=true` and a `/mail` path fails with a message that names the path.
- Local default render: the mailpit route and the Swagger UI route still exist. The current route tests stay green.
- Live check (0964 smoke, Kind with the hosted example): `GET /mail/` and `GET /docs` return 404 from the ingress.

## Definition of Done

- Render and guard tests pass. `helm lint` and `helm template` pass.
- The analytics decision (D6) is recorded in `docs/reference/hosted-profile.md`.
- `docs/how-to/test-email-signups-with-mailpit.md` and `docs/reference/platform-services.md` mark the hosted state.
- The live check runs green in the 0964 smoke job.
- `CHANGELOG.md` `[Unreleased]` entry. Recorded at merge.

## Audit Provenance

- Severity: high (public Mailpit accepts any SMTP login).
- Source audits: `.audit/research/r1-hosting.md`, sections 7 and 11 (D6). Lines were checked against `main` at `33885a70`.
