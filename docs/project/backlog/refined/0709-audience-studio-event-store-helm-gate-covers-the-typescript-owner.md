---
id: '0709'
title: Audience Studio Event-Store Helm Gate Covers the TypeScript Owner
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: audience_studio
target_release: 0.9.0
---
# TASK-0709: Audience Studio Event-Store Helm Gate Covers the TypeScript Owner

## Status
Refined. Found by the refactor audit round r1 and checked against the code by the orchestrator.

## Summary
`scripts/check_helm_event_store.py` finds only Python owners. The TypeScript audience service has no event-store flag in its template, and the gate does not see this.

## Problem Statement
- `scripts/check_helm_event_store.py:23-39`: `discover_owners` scans `*.py` files for `create_aggregate_repository(` or `AggregateRepository(`. `services/audience_studio/src/eventSourcing/repository.ts` never matches.
- `deployments/helm/runefoble/templates/audience-studio.yaml` sets `RUNEFOBLE_DATABASE_URL` but not `RUNEFOBLE_USE_POSTGRES_EVENT_STORE`. The gate contract (lines 71-72 of the script) requires it.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0005, ADR-0015.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Extend owner discovery to `*.ts` files in `src` with the pattern `new AudienceEventRepository(`. Exclude tests.
2. Add the event-store flag to `audience-studio.yaml`. The audience service must read the same flag name (check `config.ts`; if it reads another name, make the template match the service, and record the name in the gate).
3. Run `make helm-check-event-store` and fix any other gap it reports.
4. Depends on TASK-0707 for the final flag name.

## Frontdoor Blackbox Test Plan
- `make helm-check-event-store` passes on the chart.
- A test copies the chart to a temporary directory, removes the flag from the audience template, and expects the gate to exit non-zero.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r1/audience-scripts-helm.md`
