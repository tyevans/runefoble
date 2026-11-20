---
id: '0959'
title: Every Operator Credential Comes From a Named Secret in the Hosted Profile
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

# TASK-0959: Every Operator Credential Comes From a Named Secret in the Hosted Profile

## Status

Complete

## Summary

Write down the Secret keys that a hosted release needs, and make the chart read every operator credential from a named Secret. Narrow the namespace-wide `create` grant on Secrets if the input D5 allows it. The chart does not manage the Secret source. The operator chooses it (D5).

## Problem Statement

- `deployments/helm/runefoble/templates/secret.yaml:5-20` renders Secret `runefoble-credentials` with eight keys.
- `values.yaml:10-14` sets `credentials.existingSecret`. When it is set, the chart renders no Secret and reads the same keys from the named Secret.
- `templates/campaign-lore-embedding-secret.yaml:7` renders the campaign-lore key only in `local`. Hosted must create it. The name is `values.yaml:385-387` (`embeddingApiKeySecret: campaign-lore-embedding`), with key `api-key`.
- Two Secrets are generated at run time: `zitadel-admin` (key `pat`, written by the `pat-publisher` sidecar, `templates/zitadel.yaml:151-168`) and `runefoble-zitadel-client` (keys `project-id` and `client-id`, written by the bootstrap Job, `values.yaml:225-227`). Operators do not supply them.
- RBAC cannot limit `create` by name. The Zitadel Role grants `create` on all Secrets in the namespace (`templates/zitadel.yaml:23-26`). The bootstrap Role has the same grant (`templates/zitadel-bootstrap.yaml:31-34`).
- The Secret writer `libs/runefoble_auth/src/runefoble_auth/kubernetes_secret.py:34-44` uses server-side apply. Server-side apply needs `create` on a new Secret.
- The Silo access keys must be URL-safe. `templates/silo-buckets-job.yaml:6-8` builds `MC_HOST_silo` from them.
- No external-secret operator, sealed-secret, or SOPS template exists in the chart (search found none).

## Documentation & Architecture Review

- ADR-0015 (e): service credentials live in a Kubernetes Secret and are mounted into the calling pod. This record follows that rule for every operator credential.
- ADR-0015 (c): no secret in a query string or log.
- `docs/reference/identity-and-token-contract.md`: lists the service credential and the token claims. Link the new reference page from it.
- New reference page: `docs/reference/hosted-secrets.md`. Create it. It is a generic contract for every operator.

## Product & User Story References

- PRD-0025, Checkable Outcome 4 (no `DEV-ONLY` value in a hosted render) and "What good looks like" 8 (private credentials).
- No user story. This is platform work.

## Detailed Specification & Implementation Plan

1. Write `docs/reference/hosted-secrets.md`. It has one table with these columns: Secret name, key, consumer, generated or operator-supplied, rotation effect, and format rule. The table lists:
   - the Secret named in `credentials.existingSecret`: `silo-access-key`, `silo-secret-key` (URL-safe), `zitadel-masterkey` (32 bytes), `zitadel-admin-password`, `spicedb-preshared-key`, `postgres-password`, `grafana-admin-password`, `service-credential`;
   - `smtp-password` (added by record 0958, read through `zitadel.smtp.passwordSecretKey`);
   - the campaign-lore Secret (`services.campaignLore.embeddingApiKeySecret`), key `api-key`;
   - the backup Secret (planned by record 0961, keys `access-key` and `secret-key`), listed as planned;
   - the two generated Secrets, marked as generated.
2. The eight keys in `templates/secret.yaml` stay the same. Add `smtp-password` to that Secret for local rendering with an empty value. Update the pinned key set in `tests/test_blackbox_helm_secrets.py`.
3. Operator secret source (input D5). The chart reads the names only. Any of these sources works if it creates the same names: a hand-applied Secret, or an external-secret operator that writes the same Secret. The chart does not depend on the choice.
4. Narrow the `create` grant. Input D5b chooses one of two options:
   - Option A (default): keep server-side apply with `create`. Document the residual risk in `docs/reference/hosted-secrets.md`.
   - Option B: the chart renders the two generated Secrets with no data. The Roles then need only `get` and `patch` by name. Writers switch from create to patch in `kubernetes_secret.py`. A Helm upgrade must keep the data that the writers add. Test it in the smoke job (0964).
5. The hosted guard (0955) checks that `services.campaignLore.embeddingApiKeySecret` is not empty when `global.environment` is not `local`.
6. Silo keys must be URL-safe. The chart cannot read the content of an operator Secret at render time. The reference page states the pattern. The smoke job (0964) proves it: the bucket Job must succeed.

Rules for this record:
- No secret value appears in a values file, a template, or a doc.
- No fallback. A missing key fails when the workload starts.

### Inputs (user decisions)

- D5: Secret source (hand-applied Secret, or an external-secret operator).
- D5b: Option A or Option B in section 4. Default: Option A.

## Frontdoor Blackbox Test Plan

Extend `tests/test_blackbox_helm_secrets.py` and add `tests/test_blackbox_helm_hosted_secrets.py`. Both read rendered output only, plus the reference page.

- The pinned key set equals the list in the reference table (parse the Markdown table; the test fails if the two differ).
- Hosted render with `credentials.existingSecret=team-credentials`: every credential env var reads `team-credentials` with the same key names. No plain value holds a credential.
- Hosted render: the campaign-lore pod reads the `api-key` key from the named Secret. The chart renders no Secret with that name.
- Option B only: the rendered generated Secrets have no data and the Roles grant `get` and `patch` by name only.
- Live check (0964 smoke, Kind): after a Helm upgrade, the `zitadel-admin` and `runefoble-zitadel-client` data is still present.

## Definition of Done

- Tests pass. `helm lint` and `helm template` pass.
- `docs/reference/hosted-secrets.md` exists, lists every key, and is linked from `docs/reference/identity-and-token-contract.md`.
- D5 and D5b are recorded in `docs/reference/hosted-profile.md`.
- `CHANGELOG.md` `[Unreleased]` entry. Recorded at merge.

## Audit Provenance

- Severity: high (credentials are public defaults in the repository).
- Source audits: `.audit/research/r1-hosting.md`, sections 6 and 11 (D5). Lines were checked against `main` at `33885a70`.
