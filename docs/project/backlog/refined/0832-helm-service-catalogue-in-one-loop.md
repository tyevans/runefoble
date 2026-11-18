---
id: '0832'
title: "Helm Renders the Service Catalogue From One Values Map"
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0005
governing_prds: []
governing_stories: []
target_bc: deployments
target_release: 0.9.0
---

# TASK-0832: Helm Renders the Service Catalogue From One Values Map

## Status
Refined

## Summary
Four side templates repeat the services env block, the service catalogue (ports and URLs) is stated in at least five places, Silo buckets are listed but never created, and tooling has dead or overlapping files.

## Problem Statement
- Findings INF-02, INF-03, INF-04, INF-07, INF-08 in `.audit/research/infra-tooling.md` give every location (path:line). Check each against main before you change it.

## Documentation & Architecture Review
- AGENTS.md (SOLID, DDD, Hard Invariants 1, 2, 6, 7; DoR 9: no shims or aliases).
- ADR-0005.

## Product & User Story References
None. Refactor and consolidation chosen by the user on 2026-11-18.

## Detailed Specification & Implementation Plan
1. One values map drives services, URLs and Swagger entries. Fold the four side templates into the loop where they only repeat it.
2. Create the listed Silo buckets (a Helm job or service start-up), or delete the unused list.
3. Delete dead `tools/project_visualizer/graph.py` and the shell wrappers that only repeat make targets.

## Frontdoor Blackbox Test Plan
- `helm lint`, `helm template` and the Helm tests pass; the rendered env per service is unchanged (diff before and after).

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: refactor
- Source audits: `.audit/research/infra-tooling.md` (INF-02, INF-03, INF-04, INF-07, INF-08)
