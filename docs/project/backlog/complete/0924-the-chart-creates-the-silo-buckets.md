---
id: '0924'
title: The Chart Creates the Silo Buckets, and Silo Failures Are Logged
status: Complete
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---

# TASK-0924: The Chart Creates the Silo Buckets, and Silo Failures Are Logged

## Status

Complete

## Summary

The Helm chart creates no Silo buckets. `values.yaml` asks an operator to create `runefoble-assets` and `runefoble-recordings` by hand after Silo starts. After TASK-0881 moved Silo to a StatefulSet with a new volume, the buckets did not exist, and every forge request answered 503. asset_forge logged nothing, so the cause was hidden. A fresh cluster has the same defect.

## Problem Statement

- `deployments/helm/runefoble/values.yaml:161-162`: "The chart creates no buckets."
- `kubectl exec silo-0 -- ls /data` shows only `.minio.sys`.
- `services/asset_forge/src/asset_forge/silo_upload.py:40-44`: `AssetStorageError` becomes HTTP 503 with no log line. The gateway logs only `Upstream asset_forge failed with HTTP 503`.
- Failing scenarios: `asset_forge.feature` (preview, PDF export), `asset_forge_composition.feature` (preview).

## Documentation & Architecture Review

- `docs/reference/platform-services.md` (Silo), `deployments/helm/runefoble/templates/silo.yaml`.
- ADR-0005: the chart brings up a working stack. ADR-0015: failures are visible.

## Product & User Story References

None. Deployability.

## Detailed Specification & Implementation Plan

1. Add a Helm hook Job (post-install and post-upgrade) that waits for Silo and creates every bucket in a `silo.buckets` list in `values.yaml` (`runefoble-assets`, `runefoble-recordings`). It is idempotent: an existing bucket is not an error. Use a pinned client image (MinIO `mc` from the same image source as Silo, pinned by digest) and the Silo credentials Secret.
2. Remove the manual step from `values.yaml` and `docs/reference/platform-services.md`.
3. asset_forge (and every other Silo caller that maps `AssetStorageError` to 503) logs the storage error at error level with the bucket and object key, and never logs the object bytes or credentials.

## Frontdoor Blackbox Test Plan

- Helm template test: the Job renders with the hook annotations, the bucket list and the Secret references.
- Blackbox: with a Silo double that refuses the PUT, the forge route answers 503 and an error log record names the bucket and key (caplog).
- Orchestrator on Kind: `make helm-deploy`, then `ls /data` in silo-0 shows both buckets; `asset_forge.feature` and `asset_forge_composition.feature` pass.

## Definition of Done

- Tests above pass. `helm lint` and `helm template` pass. Docs and CHANGELOG `Fixed` entry.

## Audit Provenance

- Severity: high
- Source audits: .audit/work/e2e_full2.log
