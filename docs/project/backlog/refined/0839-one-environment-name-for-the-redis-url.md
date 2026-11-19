---
id: '0839'
title: One Environment Name for the Redis URL
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds:
- PRD-0011
governing_stories:
- US-0031
target_release: 0.9.0
---

# TASK-0839: One Environment Name for the Redis URL

## Status
Refined

## Summary
The Redis URL has two environment names. `PlatformSettings.redis_url` accepts `RUNEFOBLE_REDIS_URL` and `REDIS_URL` (`libs/runefoble_platform/src/runefoble_platform/config.py`, `AliasChoices`). Audience Studio reads `REDIS_URL || RUNEFOBLE_REDIS_URL` (`services/audience_studio/src/adapters.ts`). Helm sets both (`deployments/helm/runefoble/templates/services.yaml`). Two names for one setting is a compatibility alias (DoR 9). Keep `RUNEFOBLE_REDIS_URL` only, like every other platform setting.

## Documentation & Architecture Review
- `docs/reference/platform-services.md`, `docs/reference/audience-studio-api.md`, `docs/reference/cli-interfaces.md`, `docs/how-to/orchestrate-audience-chaos-polls.md` name `REDIS_URL`.
- ADR-0015 (no fallbacks), ADR-0005 (Helm).

## Product & User Story References
- [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- [`us-0031-live-stream-audience-chaos-polls-and-rumors.md`](../../user_stories/accepted/us-0031-live-stream-audience-chaos-polls-and-rumors.md)

## Detailed Specification & Implementation Plan
1. `PlatformSettings.redis_url` reads `RUNEFOBLE_REDIS_URL` only.
2. Audience Studio reads `RUNEFOBLE_REDIS_URL` only. Its start-up error names that variable.
3. Helm renders `RUNEFOBLE_REDIS_URL` only.
4. Update every test, script (`scripts/dev_orchestrator/`, CI workflow) and doc that sets or names `REDIS_URL`.
5. Also check `normalizePostgresUrl` in `services/audience_studio/src/adapters.ts`. Helm gives Audience Studio a plain `postgresql://` URL. If no deployed path sends the SQLAlchemy form, remove the rewrite.

## Frontdoor Test Plan
- Audience Studio start-up with only `REDIS_URL` set fails and names `RUNEFOBLE_REDIS_URL`.
- A Python service started with only `REDIS_URL` set does not connect to that Redis.
- `helm template` output has no `REDIS_URL` variable.

## INVEST Criteria Evaluation
Small: one setting, many call sites, no new code. Testable through process start-up and the rendered chart.

## Definition of Done
1. One environment name for the Redis URL. 2. Tests, Helm and docs updated. 3. `make health-check` passes.
