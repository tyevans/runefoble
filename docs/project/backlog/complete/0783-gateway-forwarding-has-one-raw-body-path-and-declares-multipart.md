---
id: '0783'
title: Gateway Forwarding Has One Raw-Body Path and Declares python-multipart
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: gateway_api
target_release: 0.9.0
---

# TASK-0783: Gateway Forwarding Has One Raw-Body Path and Declares python-multipart

## Status
Complete

## Summary
`forward_bytes` and `forward_raw` duplicate the raw-body forwarding logic. The services that parse multipart forms import `python-multipart` through FastAPI, but no package declares it.

## Problem Statement
- `gateway/api/src/gateway_api/` forwarding helpers: `forward_bytes` and `forward_raw` hold the same send, decode and error mapping.
- `services/asset_forge/pyproject.toml` (and any other package that parses forms): no `python-multipart` dependency.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Keep one raw-body forwarding function. Update every call site directly (DoR 9: no alias).
2. Declare `python-multipart` in each package that parses multipart forms, through `uv add`.

## Frontdoor Blackbox Test Plan
- Existing gateway proxy tests for upload and binary routes pass with the one function.
- `uv sync` in a clean environment installs `python-multipart` for asset_forge.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `.audit/work/0775.md` (Discovered)
