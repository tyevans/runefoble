---
id: '0526'
title: Zitadel OIDC Application, Issuer Consistency, and Runtime Config for Kind and Helm
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0005
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0062
target_release: 0.9.0
---

# TASK-0526: Zitadel OIDC Application, Issuer Consistency, and Runtime Config for Kind and Helm

## Status
Complete

## Summary
Wire the real Zitadel container so that a browser can sign in and every service can verify the result. Today the issuer is an in-cluster URL that a browser cannot reach, no OIDC application exists, and the frontend has no runtime configuration. Provision the application idempotently, make `iss` match the browser-facing issuer, and render the frontend runtime config from Helm.

## Problem Statement
- `deployments/helm/runefoble/values.yaml:118-124` configures Zitadel with a literal admin password and master key. This is also covered by TASK-0626. Coordinate; do not duplicate.
- `deployments/helm/runefoble/templates/zitadel.yaml:21` starts Zitadel with `start-from-init --tlsMode disabled`. No external domain is set. No OIDC application is provisioned.
- Every service receives `RUNEFOBLE_ZITADEL_ISSUER=http://zitadel:{port}` (for example `asset-forge.yaml:45-46`). A browser cannot reach this host, so a PKCE sign-in cannot complete.
- The ingress has no route to Zitadel for the browser. Audit w3-authz F20 records the path-routing gap.
- The frontend has no `runtime-config.json`. Nothing supplies the issuer or client id to the App Shell.
- `docs/tutorials/01-local-development-setup.md` does not describe a Zitadel login step.

## Documentation & Architecture Review
- ADR-0005 (Kubernetes-first, Helm and Kind) names Zitadel. Update the tutorial and the platform reference.
- TASK-0520 requires `iss` to equal the configured issuer and JWKS to come from the internal URL. This task makes both true in the cluster.
- TASK-0624 and TASK-0622 edit `services.yaml` and `values.yaml`. TASK-0620 edits image wiring. Merge these carefully (see the index report).

## Product & User Story References
- PRD-0023 (OIDC sign-in) and US-0062 (sign-up and sign-in).

## Detailed Specification & Implementation Plan
1. **Issuer consistency**
   - Set Zitadel's external domain and port to the browser-facing host (for example `localhost` through Traefik on port 80, or a dedicated host).
   - Every service and the gateway set `RUNEFOBLE_ZITADEL_ISSUER` to that external URL. This is the value that Zitadel writes into `iss`.
   - Set `RUNEFOBLE_ZITADEL_JWKS_URL` to the in-cluster URL of the `jwks_uri` from discovery (`http://zitadel:8080/...`).
   - Set `RUNEFOBLE_ZITADEL_AUDIENCE` to the API project audience.
2. **Ingress**: add a route from the ingress to Zitadel for the external domain (path or host). Verify that `GET <external>/.well-known/openid-configuration` returns 200 from the host.
3. **Bootstrap Job (Helm hook, idempotent)**
   - Creates the `runefoble` project, the API audience, and a public PKCE application `runefoble-web`. Allowed redirect URI: the App Shell callback. Allowed post-logout URI: the App Shell root.
   - Creates a machine user with a personal access token for the test suite and for the Playwright setup. Store the token in a Kubernetes Secret. Do not write it to git.
   - Re-running the Job does not duplicate objects.
   - Check the Zitadel v2.54 management API details with Context7 before implementing. Do not rely on memory.
4. **Local admin bootstrap**: the first admin user is created by the Job or by `make seed-admin`. This replaces the deleted gateway route (TASK-0523). The gateway does not create admins.
5. **Runtime config**: the frontend chart renders `runtime-config.json` (issuer, client id, scopes, provider name) from values. Nginx serves it at `/runtime-config.json`. No secret is in this file.
6. **Kind values**: no dev-mode switch. Local developers run the same flow as production, with the Zitadel container.
7. **Docs**: update `docs/tutorials/01-local-development-setup.md` with the Zitadel first-run step. Update `docs/reference/platform-services.md` with the three issuer variables and their meaning.

## Frontdoor Blackbox Test Plan
Infrastructure checks through public HTTP only (executed by `make health-check` and the e2e setup).
- Before: `GET /runtime-config.json` returns 404. The discovery URL is not reachable through the ingress.
- After:
  - `GET /runtime-config.json` returns the issuer and client id from values.
  - Discovery through the ingress returns 200. Its `issuer` equals `RUNEFOBLE_ZITADEL_ISSUER`.
  - A token from a real sign-in (TASK-0525) has `iss` equal to the configured issuer and `aud` equal to the configured audience. The gateway accepts it.
  - `helm lint` and `helm template` render the Job, the config map, and the new environment variables.

## Definition of Done
1. `helm lint deployments/helm/runefoble` and `helm template` pass.
2. `make health-check` passes on a Kind cluster with the Zitadel bootstrap run.
3. Re-running the bootstrap Job makes no changes (idempotent). Show the second run output.
4. Tutorial and platform reference are updated.
5. No secret value is committed. The admin password literal is removed in TASK-0626, not here.

## Audit Provenance

- Severity: critical
- Source audits: `w3-ddd-architecture.md`, `w2-app-shell.md`, `w1-gates-infra.md`, `w3-docs-integrity.md`
