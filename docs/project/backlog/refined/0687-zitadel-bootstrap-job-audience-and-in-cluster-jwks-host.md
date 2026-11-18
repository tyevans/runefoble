---
id: '0687'
title: Zitadel Bootstrap Job, Token Audience, Generated Client ID, and In-Cluster JWKS Host
status: Refined
created: 2026-11-17
dependencies:
- TASK-0526
- TASK-0527
- TASK-0626
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds:
- PRD-0023
governing_stories:
- US-0062
target_release: 0.9.0
---

# TASK-0687: Zitadel Bootstrap Job, Token Audience, Generated Client ID, and In-Cluster JWKS Host

## Status
Refined. Discovered in round 2 audit of reports 0526, 0523 and 0524. TASK-0526 is complete, but its live Kind checks and the bootstrap were not built. Blocks sign-in and token verification in the cluster.

## Summary
The chart runs Zitadel, but nothing provisions the OIDC project and application. Zitadel generates the project ID and the client ID at run time, so the chart cannot set them. Services also fetch JWKS from the in-cluster host, while Zitadel accepts only its configured host. This task adds a bootstrap Job, sets the token audience, passes the generated client ID to the App Shell and the services, and adds a verifier setting for the in-cluster JWKS Host header.

## Problem Statement
- `deployments/helm/runefoble/templates/zitadel.yaml` has no bootstrap Job. Nothing creates the project `runefoble`, the web application `runefoble-web`, or its redirect URIs `http://localhost/auth/callback` and `http://localhost/`.
- `values.yaml` `frontend.runtimeConfig.clientId` is empty. Sign-in fails with "Zitadel client ID is not configured".
- `RUNEFOBLE_ZITADEL_AUDIENCE` is not set. The verifier default `runefoble-api` does not match the `aud` claim. Zitadel puts the project ID in `aud` only when the client requests the project audience scope. The App Shell does not request it (report 0524).
- Services fetch `http://zitadel:8080/oauth/v2/keys` and send `Host: zitadel:8080`. Zitadel serves only `auth.localhost`, so it may answer "Instance not found" (report 0526). Live check not done.
- `make seed-admin` was removed by TASK-0523. No replacement creates a local admin.

## Documentation & Architecture Review
- ADR-0015 (c): every service verifies the Zitadel JWT itself. This task makes that check work in the cluster.
- ADR-0015 (d): registration and sign-in use Zitadel hosted pages and PKCE.
- `docs/reference/platform-services.md` line 66 describes the JWKS URL. Update it with the Host setting.

## Product & User Story References
- PRD-0023 and US-0062 (registration, Zitadel OIDC, profile).

## Detailed Specification & Implementation Plan
1. Add a Helm post-install and post-upgrade hook Job. It uses the Zitadel management API to create or find the project `runefoble` and the OIDC application `runefoble-web` (PKCE, no client secret, redirect and post-logout URIs from values). It must be idempotent: a second run changes nothing.
2. Admin credential for the Job: take it from a Kubernetes Secret created by TASK-0626. Pick one source and document it. Do not read files from the Zitadel container.
3. The Job writes the generated project ID and client ID to a Secret `runefoble-zitadel-client`. The App Shell runtime config and the services read these at start. Remove the empty `clientId` value.
4. Audience: the App Shell requests the scope `urn:zitadel:iam:org:project:id:<projectId>:aud`. Services set `RUNEFOBLE_ZITADEL_AUDIENCE` to the project ID from the Secret.
5. In-cluster JWKS: add a verifier setting (for example `RUNEFOBLE_ZITADEL_HOST_HEADER`) that sets the `Host` header on JWKS and discovery requests. Confirm that the pinned PyJWT `PyJWKClient` accepts custom headers. If not, fetch the key set with httpx and pass the key to PyJWT. Do not rewrite the issuer or disable the `iss` check.
6. Keep `auth.localhost` and plain HTTP as local Kind values only. Document the production values.

## Frontdoor Blackbox Test Plan
- Live Kind (manual gate, recorded in the report): `helm install`, the Job completes, a second `helm upgrade` leaves the project and app unchanged.
- Sign-in through the App Shell (TASK-0525 journey) returns an access token. The gateway accepts it (HTTP 200 on a campaign list route).
- A token with another audience is refused (TASK-0535 negative suite).
- The services start with the Host setting and fetch JWKS without error.

## Definition of Done
- Bootstrap Job, Secret, audience and Host setting exist in the chart and in the verifier.
- `helm lint` and `helm template` pass. `make health-check` passes.
- Docs updated: `platform-services.md`, `authenticate-with-zitadel-oidc.md`.

## Audit Provenance

- Severity: high
- Source audits: `work/0526.md`, `work/0523.md`, `work/0524.md`
