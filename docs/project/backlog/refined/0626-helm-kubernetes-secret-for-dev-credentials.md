---
id: '0626'
title: Move Chart Credentials to a Kubernetes Secret
status: Refined
created: 2026-11-17
dependencies:
- TASK-0625
governing_adrs:
- ADR-0005
- ADR-0001
governing_prds: []
governing_stories: []
target_release: 0.9.0
severity: medium
source_audits:
- w1-gateway-api.md
- w1-gates-infra.md
---

# TASK-0626: Move Chart Credentials to a Kubernetes Secret

## Status
Refined

## Summary
`deployments/helm/runefoble/values.yaml` commits credentials in plain text, and the templates render them as literal container `env.value` entries. Generate one Kubernetes Secret from values, reference it with `secretKeyRef` in every container, and keep the local development values only in the tutorial, clearly labelled as dev-only.

## Problem Statement
- `values.yaml` contains `silo.secretKey: silo_secret_pass`, `zitadel.adminPassword: RunefobleAdminPassword123!`, `zitadel.masterKey`, `spicedb.presharedKey: runefoble_secret_key`, `grafana.adminPassword: admin` (`w1-gates-infra.md` F11).
- Templates such as `soundscape.yaml` and `asset-forge.yaml` render `RUNEFOBLE_SILO_SECRET_KEY` as a literal value. `spicedb.yaml` passes the key as a container argument (visible in `kubectl describe`).
- `w1-gateway-api.md` F3 and F2 are auth issues handled elsewhere; this task only covers secret storage.

## Documentation & Architecture Review
- `docs/tutorials/01-local-development-setup.md` should hold the dev defaults, labelled "dev-only, never for shared clusters".
- ADR-0005 governs chart layout.

## Product & User Story References
- None; platform hygiene.

## Detailed Specification & Implementation Plan
1. Add `templates/secret.yaml` rendering a Secret `runefoble-credentials` from a new `credentials:` values block (`silo.accessKey`, `silo.secretKey`, `zitadel.masterKey`, `zitadel.adminPassword`, `spicedb.presharedKey`, `postgres.password`, `grafana.adminPassword`). Support `credentials.existingSecret` to skip rendering.
2. Replace literal `value:` for each secret env var with `valueFrom.secretKeyRef` in every template (`services.yaml`, `soundscape.yaml`, `asset-forge.yaml`, `audience-studio.yaml`, `campaign-analytics.yaml`, `spicedb.yaml`, `zitadel.yaml`, `silo.yaml`, `postgres.yaml`, `observability.yaml`).
3. SpiceDB: pass the preshared key through an env var (`SPICEDB_GRPC_PRESHARED_KEY`) instead of an argument, and reference the Secret.
4. Keep `values.yaml` defaults for local development only; add a comment that they are dev-only, and set `global.environment` checks so a non-local environment fails `helm template` when `credentials.existingSecret` is empty and the dev defaults are used (`required` function).
5. Update the local tutorial with the `make` target or steps that create the dev secret.

## Frontdoor Blackbox Test Plan
- Before fix: `helm template ... | grep 'runefoble_secret_key'` finds the key in container specs.
- After fix: rendered Deployments contain no literal secret value; a pytest test (`tests/test_blackbox_helm_secrets.py`) renders the chart and asserts no container env `value` matches a credentials key, and that `helm template -f values-prod-sample.yaml` with no existing secret fails.
- Through HTTP: after `helm upgrade`, `GET /api/v1/health` still returns 200 (manual gate in a Kind cluster).

## Definition of Done
1. No secret literal in rendered container specs.
2. Secret template and secretKeyRef wiring render and lint.
3. Dev defaults documented as dev-only.
4. `helm lint` and `helm template` pass.
5. No file above 500 lines.
