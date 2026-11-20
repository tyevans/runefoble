---
id: '0960'
title: Image Registry Value and Digest Pins for Every Hosted Image
status: Complete
created: 2026-11-19
dependencies:
- '0955'
governing_adrs:
- ADR-0005
- ADR-0010
governing_prds:
- PRD-0025
governing_stories: []
target_bc: core
target_release: 1.0.0
---

# TASK-0960: Image Registry Value and Digest Pins for Every Hosted Image

## Status

Complete

## Summary

A hosted install pulls images from a registry, not from the local Kind cache. Add a push target and a values file that holds full image references with digests. Pin every third-party image and the Python base images by digest. Add pull secrets for the private registry.

## Problem Statement

- `Makefile:114-133` (`images`) builds every image and loads it into Kind (`kind load` at `Makefile:124`, `:129`, `:133`). Nothing pushes an image.
- `Makefile:93-106` (`PYTHON_IMAGE_ROWS`) lists the Python images. Names have no registry prefix.
- `deployments/helm/runefoble/values.yaml:300` and `values.yaml:467` set images such as `runefoble/gateway-api:0.1.0`. The chart renders `image:` as written (`templates/services.yaml:40`).
- Third-party images are pinned by tag only: Postgres `values.yaml:138`, Redis `values.yaml:152`, Zitadel `values.yaml:193`, SpiceDB `values.yaml:232`, SpiceDB schema client `values.yaml:237`, OpenPanel `values.yaml:243`, Mailpit `values.yaml:249`, OTel `values.yaml:258`, Loki `values.yaml:262`, Grafana `values.yaml:265`, Swagger UI `values.yaml:271`.
- Two images already use a digest: Silo `values.yaml:170` and the Silo client `values.yaml:181`.
- The Python base image is `python:${PYTHON_VERSION}-slim` with no digest (`deployments/docker/python-service.Dockerfile:20`). The uv image is pinned by tag (`Dockerfile:18`, `:16`).
- No `imagePullSecrets` appears in the chart (search found none).
- `Makefile:79` installs Traefik with the latest chart from the repository. No version is set. This affects Kind only, but the hosted operator must pin it too (runbook, 0965).

## Documentation & Architecture Review

- ADR-0005: CI and cloud clusters use the same chart. This record adds values and a push target. It does not add a second chart.
- ADR-0010 (`docs/project/adrs/accepted/adr-0010-continuous-integration-pipeline.md`): CI owns the image build. The push job lives in CI (0964).
- `tests/test_blackbox_deployability_images.py`: checks that the image table matches the chart and that `make -n images` lists each row. Extend it.
- `docs/reference/cli-interfaces.md`: lists Makefile targets. Add `images-push`.

## Product & User Story References

- PRD-0025, Checkable Outcome 6 (CI builds images and installs the chart).
- No user story. This is platform work.

## Detailed Specification & Implementation Plan

1. Makefile:
   - Add `IMAGE_REGISTRY ?=` (empty means local names). Add `images-push` that builds, tags, and pushes every row of `PYTHON_IMAGE_ROWS`, the audience-studio image, and the frontend image. It prints each digest.
   - Add a step that writes the digests to `deployments/helm/runefoble/values.images.yaml`. This file holds full references: `<registry>/runefoble/<name>:<version>@sha256:<digest>`. The release commits it.
   - Keep `images` and `kind load` for local work.
2. Chart:
   - Add `values.images.yaml` as an optional `-f` file. It overrides `image:` keys with the full references. Do not change `values.yaml` (line count, see 0955).
   - Add `global.imagePullSecrets` as a list read with `default`. When set, every pod spec renders `imagePullSecrets`. Templates: `services.yaml`, `zitadel.yaml`, `zitadel-bootstrap.yaml`, and the other workload templates.
3. Digests:
   - Pin each third-party image by digest in `values.images.yaml`. Resolve the digests at implementation time (for example with `docker buildx imagetools inspect`). The digests are inputs (D2b).
   - Pin the Python base (`python-service.Dockerfile:20`) and the uv image (`:18`) by digest in the Dockerfile. Keep the tag as a comment.
4. Hosted guard (0955): fail when any image in a hosted render has no registry host, or when a third-party image has no `@sha256:`.

Rules for this record:
- A hosted render never uses a `runefoble/...` name without a registry.
- Do not change tags in `values.yaml`. The local profile keeps them.

### Inputs (user decisions)

- D2: image registry host and path (for example a managed registry in the operator's account), and the storage class and cluster provider (not in this record).
- D2b: the pull secret name (`global.imagePullSecrets`) and the registry credential. Store it through record 0959.
- D2c: whether images are pushed by CI on `main` only (default) or by hand.

## Frontdoor Blackbox Test Plan

Extend `tests/test_blackbox_deployability_images.py` and add `tests/test_blackbox_helm_image_pins.py`.

- `make -n images-push` lists each image row, a `docker push`, and the digest step. It does not push.
- Hosted render with a copy of `values.images.yaml` (test values with a test registry name): every `runefoble/*` image has the registry prefix and a digest. Every third-party image has `@sha256:`.
- The guard rejects a hosted render where one third-party image has no digest.
- With `global.imagePullSecrets` set, every Deployment and StatefulSet pod spec and every Job pod spec carries `imagePullSecrets`.
- Local default render: image names match `make images` tags (the existing test `test_helm_template_image_tags_match_built_tags`).
- Live check (0964 smoke): the images pull from a registry in CI, and the cluster starts every pod.

## Definition of Done

- Tests pass. `helm lint` and `helm template` pass in local and hosted modes.
- `values.images.yaml` exists after a release push and holds a digest for every image.
- `docs/reference/cli-interfaces.md` lists `images-push`.
- The Dockerfile digests are documented in the runbook (0965).
- `CHANGELOG.md` `[Unreleased]` entry. Recorded at merge.

## Audit Provenance

- Severity: high (a hosted install cannot pull images from a local Kind cache).
- Source audits: `.audit/research/r1-hosting.md`, sections 8 and 11 (D2). Lines were checked against `main` at `33885a70`. The research cites `Makefile:39-58` for `images`; the target is at `Makefile:114-133`.
