---
id: '0955'
title: Hosted Values Profile and Dev-Default Render Guard
status: Refined
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds:
- PRD-0025
governing_stories: []
target_bc: core
target_release: 1.0.0
---

# TASK-0955: Hosted Values Profile and Dev-Default Render Guard

## Status

Refined. Release One hosting slice 1 of 11 (PRD-0025, outcome 4). Other hosting records depend on this one.

## Summary

Add a hosted values file that a release operator copies and fills in. Add a render guard that makes `helm template` fail when a hosted render still uses a development default. The guard runs at render time, so a bad profile never reaches a cluster.

## Problem Statement

- `deployments/helm/runefoble/values.yaml:4` sets `global.environment: local`. This is the only switch that turns on the stricter checks.
- `deployments/helm/runefoble/values.yaml:8-9` marks the credential defaults as `DEV-ONLY` and public.
- `deployments/helm/runefoble/templates/secret.yaml:1-4` fails only when `credentials.existingSecret` is empty and the environment is not `local`. No other development default is checked.
- Other development defaults that reach a hosted render today: `values.yaml:224` (`zitadel.bootstrap.devMode: true`), `values.yaml:214` (PAT expiry `2099-01-01`), `values.yaml:200` (admin e-mail on `runefoble.local`), `values.yaml:219-222` (localhost redirect URIs), `values.yaml:248` (`mailpit.enabled: true`), `values.yaml:38` and `values.yaml:82` (hosts `runefoble.local` and `localhost`).
- `deployments/helm/runefoble/values.yaml` has 501 lines. This is above the 500-line invariant (AGENTS.md, Hard Invariant 6). This record must add no line to `values.yaml`. Hosted keys go in the new example file.
- `Makefile:158` (`helm-deploy`) loads `values.local.yaml` when that file exists. A hosted release must not use this target.
- Existing test: `tests/test_blackbox_helm_secrets.py:125-130` checks only the `existingSecret` guard.

## Documentation & Architecture Review

- ADR-0005 (`docs/project/adrs/accepted/adr-0005-kubernetes-first-infrastructure-with-helm-and-kind.md`): one umbrella chart. CI and cloud clusters deploy the same chart. The hosted profile is values only, not a second chart.
- ADR-0015 (`docs/project/adrs/accepted/adr-0015-audit-remediation-decisions.md`), decisions (c) and (f): development modes fail closed in deployed environments. No substitute output.
- `docs/reference/platform-services.md`: the reference for external platform services. The new reference page for the hosted profile is `docs/reference/hosted-profile.md`. Create it. It is a generic pattern that the runbook (0965) uses.
- `docs/reference/cli-interfaces.md`: lists `make helm-deploy`. Add a note that hosted releases do not use it.

## Product & User Story References

- PRD-0025 (`docs/project/product/accepted/prd-0025-voice-first-release-one.md`), Checkable Outcome 4: the hosted profile renders with no development default, and a render guard fails on any `DEV-ONLY` value.
- No user story. This is platform work.

## Detailed Specification & Implementation Plan

1. Create `deployments/helm/runefoble/values.hosted.example.yaml`. It sets `global.environment: production`, `credentials.existingSecret` (name only), the ingress hosts, the Zitadel public settings, and `mailpit.enabled: false`. Every host name and e-mail address uses the placeholder marker `REPLACE-ME`. The file has no credential value.
2. Create `deployments/helm/runefoble/templates/hosted-guard.yaml`. The file renders no object. When `global.environment` is `staging` or `production`, it calls `fail` on the first violated key. It checks:
   a. Any ingress host or `global.domain` contains `REPLACE-ME`, equals `localhost`, or ends with `.local`.
   b. `mailpit.enabled` is `true`.
   c. `zitadel.bootstrap.devMode` is `true`.
   d. `zitadel.externalSecure` is `false`.
   e. `zitadel.bootstrap.patExpirationDate` starts with `2099`.
   f. Any redirect or post-logout URI starts with `http://`, or contains `localhost`.
   g. `zitadel.adminEmail` contains `REPLACE-ME` or ends with `@runefoble.local`.
   The message names the key path and the value that failed.
3. The guard reads each key that `values.yaml` marks `DEV-ONLY`. When `credentials.existingSecret` is set, the chart does not render those values. The frontdoor test below proves that no rendered manifest contains a `DEV-ONLY` literal.
4. Keep the local render unchanged. The guard is inactive for `local`.
5. Create `docs/reference/hosted-profile.md`. It lists every hosted key, the check that guards it, and the placeholder marker.
6. Add a note in `docs/reference/cli-interfaces.md` that `make helm-deploy` loads `values.local.yaml` and is not a hosted install path.

Rules for this record:
- Do not change `values.yaml`.
- Do not add a fallback. An unset hosted key fails the render. It never takes a development value.

### Inputs (user decisions)

- D1: the public host names and the apex domain (replaces `REPLACE-ME`).
- D7: the first admin e-mail address (`zitadel.adminEmail`).

## Frontdoor Blackbox Test Plan

New file: `tests/test_blackbox_helm_hosted_profile.py`. It uses `tests/helpers/helm.py` (`helm_template_result`, `render_chart`). It reads only rendered output and the example file.

- The example as shipped: `helm template -f values.hosted.example.yaml` exits non-zero. The message names the first key that holds `REPLACE-ME`.
- A copy of the example in `tmp_path` with `REPLACE-ME` replaced by `hosted-test` renders with exit code 0.
- Parametrized: from that copy, set each violating value in turn (`mailpit.enabled=true`, `zitadel.bootstrap.devMode=true`, `zitadel.externalSecure=false`, `zitadel.bootstrap.patExpirationDate=2099-01-01T00:00:00Z`, `zitadel.adminEmail=admin@runefoble.local`, an `http://` redirect URI). Each render fails and the message names that key.
- The rendered output of the valid copy contains no `DEV-ONLY` literal from `values.yaml` (parse the `credentials` block to get the literals).
- The default local render still passes the existing tests in `tests/test_blackbox_helm_secrets.py` and `tests/test_blackbox_helm_ingress_ws.py`.
- `helm lint deployments/helm/runefoble` exits 0.

## Definition of Done

- Frontdoor tests pass through `uv run pytest`.
- `helm lint` and `helm template` pass for the local render and for the hosted copy.
- `values.yaml` line count does not grow.
- `docs/reference/hosted-profile.md` exists and lists every hosted key.
- `CHANGELOG.md` `[Unreleased]` entry (Added: hosted values profile and render guard). Recorded at merge, not in this record.

## Audit Provenance

- Severity: high (blocks hosted release).
- Source audits: `.audit/research/r1-hosting.md`, sections 6, 7 and 11 (D1, D7).
