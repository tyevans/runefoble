---
id: '0794'
title: Service URLs Use One RUNEFOBLE Setting Name Each and No In-Cluster Code Defaults
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: runefoble_platform
target_release: 0.9.0
---

# TASK-0794: Service URLs Use One RUNEFOBLE Setting Name Each and No In-Cluster Code Defaults

## Status
Refined. Found during batch 23 integration, 2026-11-17.

## Summary
Service address settings mix names with and without the `RUNEFOBLE_` prefix, and some keep in-cluster code defaults. A missing setting then points at a wrong host in silence. The dev server sets no gateway upstream URLs.

## Problem Statement
- The gateway reads `BOARD_STATE_URL`. Helm renders it without the prefix.
- `libs/runefoble_platform/src/runefoble_platform/config.py`: `soundscape_url` and `campaign_analytics_url` default to in-cluster hosts.
- `scripts/dev_server.py`: sets no upstream URLs, so each health probe reports `not_configured` in `make dev`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0005, ADR-0015.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Every service URL is a `PlatformSettings` field read as `RUNEFOBLE_<SERVICE>_URL`, with no default.
2. Helm renders each name once per consumer.
3. `scripts/dev_server.py` sets each URL to the local port of the service it starts.

## Frontdoor Blackbox Test Plan
- `helm template` renders only `RUNEFOBLE_*_URL` names.
- `make dev` gateway `/healthz` reports each started service as probed.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `.audit/work/0674.md`, `.audit/work/0791.md` (Discovered)
