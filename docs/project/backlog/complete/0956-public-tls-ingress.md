---
id: '0956'
title: Public TLS Ingress with an HTTP-to-HTTPS Redirect
status: Complete
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

# TASK-0956: Public TLS Ingress with an HTTP-to-HTTPS Redirect

## Status

Complete

## Summary

Add a TLS block to the application ingress, an HTTP-to-HTTPS redirect, and a certificate source that the operator chooses as a value. Local rendering stays the same. Hosted rendering serves HTTPS only.

## Problem Statement

- `deployments/helm/runefoble/values.yaml:36` sets the Traefik entrypoint to `web` only.
- `deployments/helm/runefoble/templates/ingress.yaml:9-12` renders annotations from values. The template has no `tls:` key (`ingress.yaml:1-30`).
- `deployments/helm/runefoble/values.yaml:38` and `values.yaml:82` set hosts `runefoble.local` and `localhost`. `values.yaml:128` sets `auth.localhost`.
- `frontend/nginx.conf:2` listens on port 80 only. TLS must end at the ingress.
- `Makefile:79` installs Traefik with `ports.websecure.hostPort=443`. This applies to Kind only. `Makefile:76-77` apply the Traefik CRD and chart without a pinned version.
- The browser needs a secure context for the microphone. A plain-HTTP public host refuses `getUserMedia`. `services/voice_agent/ui/src/runefoble-voice-controls.ts:87` calls `getUserMedia`, and the catch at `:91-93` hides the failure.
- No cert-manager object exists in the chart (`templates/` search finds none).

## Documentation & Architecture Review

- ADR-0005: the ingress is Traefik. Kind publishes ports 80 and 443 (`deployments/kind/cluster-config.yaml`).
- ADR-0015 (b): no substitute output. A failed TLS setup must fail the render or the certificate, not fall back to HTTP.
- `docs/reference/ports-and-endpoints.md`: the ingress routing table. Update it with the TLS and redirect rules.
- `docs/how-to/authenticate-with-zitadel-oidc.md`: the redirect URI rules. This record does not change the Zitadel values. Record 0958 does.

## Product & User Story References

- PRD-0025, "What good looks like" 8 (HTTPS on one hosted cluster) and Checkable Outcome 4 (serves HTTPS only).
- No user story. This is platform work.

## Detailed Specification & Implementation Plan

Keys are read in the template with `default`. They are not added to `values.yaml`. The hosted example (0955) sets them.

```
ingress:
  tls:
    mode: none            # none (default, local), certManager, or existingSecret
    clusterIssuer: ""     # certManager: name of the ClusterIssuer (input D3)
    secretName: ""        # existingSecret: name of a kubernetes.io/tls Secret (input D3)
  httpsRedirect: false    # true in the hosted example
```

1. When `mode` is not `none`, the application Ingress gets a `tls:` block. It lists every host in `ingress.hosts`. The `secretName` is `<release>-tls` for `certManager`, or the value of `tls.secretName` for `existingSecret`.
2. When `mode` is `certManager`, the template adds the annotation `cert-manager.io/cluster-issuer` with the value of `clusterIssuer`. The chart does not install cert-manager.
3. When `httpsRedirect` is `true`, the template renders:
   a. one Traefik `Middleware` (`apiVersion: traefik.io/v1alpha1`) with `redirectScheme` set to `https` and `permanent: true`;
   b. a second Ingress for the same hosts. It uses only the `web` entrypoint and the middleware annotation;
   c. the application Ingress uses only the `websecure` entrypoint.
   Check the annotation syntax against the Traefik version the operator installs. Record that version in the runbook (0965).
4. When `mode` is `none` and `httpsRedirect` is `false`, the render matches today's output. The WebSocket route tests stay green.
5. The guard (0955) rejects a hosted render with `mode: none` or `httpsRedirect: false`.

Rules for this record:
- Do not add lines to `values.yaml`.
- Do not render an HTTP route for an application host in hosted mode.

### Inputs (user decisions)

- D1: host names (from 0955).
- D2: ingress class is Traefik. The hosted cluster must have the Traefik CRDs installed (`Middleware`). Confirm that the operator installs them.
- D3: certificate source. Either the name of a cert-manager ClusterIssuer (ACME or a private CA), or the name of an existing TLS Secret.

## Frontdoor Blackbox Test Plan

Extend `tests/test_blackbox_helm_ingress_ws.py` with a new file `tests/test_blackbox_helm_tls_ingress.py`. It reads rendered manifests only.

- `mode=certManager`: the Ingress has a `tls` entry for every host with `secretName: runefoble-tls`, and the cluster-issuer annotation carries the chosen name.
- `mode=existingSecret`: `tls.secretName` equals the operator's name, and the issuer annotation is absent.
- `httpsRedirect=true`: one `Middleware` with `redirectScheme.scheme: https`. The redirect Ingress uses only `web`. The app Ingress uses only `websecure`.
- Default render (`mode: none`): no `tls` key, no `Middleware`, and the entrypoint annotation is `web`.
- Live check (in 0964 smoke, on Kind with a self-signed issuer): `curl -I http://<host>/` returns `301` with `Location: https://`, and `https://` returns the App Shell.

## Definition of Done

- Render tests pass. `helm lint` and `helm template` pass in both modes.
- The 0955 guard passes for the hosted example with TLS set, and fails with `mode: none`.
- `docs/reference/ports-and-endpoints.md` lists the TLS and redirect rules.
- The live check runs green in the 0964 smoke job.
- `CHANGELOG.md` `[Unreleased]` entry. Recorded at merge.

## Audit Provenance

- Severity: high (blocks hosted release; browsers refuse the microphone over HTTP).
- Source audits: `.audit/research/r1-hosting.md`, sections 2 and 11 (D3). Line references in this record were checked against `main` at `33885a70`. The research line for `Makefile:24` is wrong; the image rows are at `Makefile:93-106`.
