---
id: '0725'
title: Helm Standalone Services Share One Platform Environment Template
status: Refined
created: 2026-11-17
dependencies:
- TASK-0709
governing_adrs:
- ADR-0005
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0725: Helm Standalone Services Share One Platform Environment Template

## Status
Refined. Found by the refactor audit round r1 and checked against the code by the orchestrator.

## Summary
Five Helm templates repeat the same platform environment block with hardcoded hosts. `services.yaml` branches on service names.

## Problem Statement
- Same env set (`POSTGRES_PASSWORD`, `RUNEFOBLE_SPICEDB_PRESHARED_KEY`, `RUNEFOBLE_DATABASE_URL`, `RUNEFOBLE_SPICEDB_ENDPOINT`, `REDIS_URL`, `RUNEFOBLE_REDIS_URL`, OTel keys) in `templates/services.yaml:57`, `audience-studio.yaml`, `soundscape.yaml`, `campaign-analytics.yaml`, `asset-forge.yaml`.
- Hardcoded hosts `runefoble-redis`, `postgres:5432`, `otel-collector`. The `redis.enabled` flag is ignored.
- `templates/services.yaml:88`: credential grant list hard-coded by name. `:98` and `:115`: two `eq .name "voice-agent"` branches. `:19-30`: consumer URL map in the template.
- `values.yaml:316`: stale comment `Expected token aud claim`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0005.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add `_helpers.tpl` named templates `runefoble.platformEnv`, `runefoble.databaseUrl` (scheme as parameter) and `runefoble.redisUrl`. Convert the five templates.
2. Move voice-agent extras, the credential list and consumer lists in `services.yaml` into `values.yaml`. Remove both `eq .name` branches.
3. Remove the stale comment.
4. Do not add Deployment and Service scaffolding templates in this slice.
5. Rendered env names and values stay the same. Compare `helm template` before and after.

## Frontdoor Blackbox Test Plan
- A test diffs `helm template` env for the five services before and after (names and values equal).
- `tests/test_blackbox_helm_service_urls.py` and `tests/test_blackbox_deployability_images.py` pass. `helm lint` passes.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `refactor-r1/audience-scripts-helm.md`
