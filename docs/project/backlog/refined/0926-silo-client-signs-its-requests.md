---
id: '0926'
title: The Silo Client Signs Its Requests, and a Test Runs Against Real MinIO
status: Refined
created: 2026-11-19
dependencies:
- '0924'
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---

# TASK-0926: The Silo Client Signs Its Requests, and a Test Runs Against Real MinIO

## Status

Refined. Found by TASK-0924 (`.audit/work/0924.md`, Discovered).

## Summary

`SiloStorageService` reads the Silo access key and secret key but sends unsigned S3 requests. The pinned Silo image (Chainguard MinIO) refuses unsigned requests with 403 even when the bucket exists. Asset upload, read and delete therefore cannot work on a deployed stack. The tests pass only because they replace the Silo HTTP boundary with a transport double that accepts unsigned requests.

## Problem Statement

- `libs/runefoble_platform/src/runefoble_platform/storage.py:66-87`: the keys are stored and never used. `_request` (`:109-116`) sends plain httpx requests.
- `tests/helpers/silo_fixtures.py`: the transport double does not check signatures.
- Local check in TASK-0924: the pinned image answers 403 to an unsigned PUT into an existing bucket.

## Documentation & Architecture Review

- `docs/reference/platform-services.md` (Silo), `docs/reference/browser-asset-reads.md`.
- ADR-0015: failures are visible; no test double that hides a production defect.

## Product & User Story References

None. Every asset flow (forge, wardrobe, print, uploads) depends on it.

## Detailed Specification & Implementation Plan

1. Sign every Silo request with AWS Signature Version 4 (service `s3`, region from a `silo_region` setting with default `us-east-1`). Use a maintained library for the signature (for example `botocore.auth.SigV4Auth` with `botocore.awsrequest.AWSRequest`), not hand-written crypto. Keep httpx and the injectable transport.
2. Missing keys in a deployed environment stop start-up with `ConfigurationError` (fail fast, as for SpiceDB).
3. The transport double in `tests/helpers/silo_fixtures.py` checks that each request has a SigV4 `Authorization` header and refuses an unsigned one with 403.
4. Add one blackbox test against a real MinIO container (same image family as the chart, testcontainers, like the PostgreSQL fixtures): create a bucket, upload, read and delete through `SiloStorageService`.
5. Add the dependency through the uv workspace only (Hard Invariant 4).

## Frontdoor Blackbox Test Plan

- Real MinIO container: signed upload, read and delete succeed; a client with a wrong secret key gets a typed `AssetStorageError`.
- Transport double: an unsigned request is refused.
- Orchestrator on Kind: `asset_forge.feature` and `asset_forge_composition.feature` pass after TASK-0924 and this task.

## Definition of Done

- Tests above pass. Docs and CHANGELOG `Fixed` entry.

## Audit Provenance

- Severity: high
- Source audits: .audit/work/0924.md
