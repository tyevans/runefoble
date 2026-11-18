---
id: '0775'
title: Gateway Depends on No Service Package
status: Complete
created: 2026-11-17
dependencies:
- TASK-0593
governing_adrs:
- ADR-0013
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: gateway
target_release: 0.9.0
---

# TASK-0775: Gateway Depends on No Service Package

## Status
Complete

## Summary
The API gateway still imports service packages and lists them as dependencies. This couples the gateway to service internals and breaks the thin-gateway rule (ADR-0015 b). Agreed at the refactor pause on 2026-11-17 (candidate 1).

## Problem Statement
- `gateway/api/src/gateway_api/routers/compendium_proxy.py:16` imports `rules_compendium.models`.
- `gateway/api/src/gateway_api/routers/soundscape.py:10` imports `soundscape.models`.
- `gateway/api/src/gateway_api/companion/*` and `signaling/*` import `voice_agent` (check what remains after TASK-0593).
- `gateway/api/pyproject.toml` lists `voice-agent`, `character-sheet`, `soundscape`, `rules-compendium` as dependencies.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0013, ADR-0015.

## Product & User Story References
None. Architecture quality.

## Detailed Specification & Implementation Plan
1. Replace every service import in `gateway/api/src` with JSON forwarding (`forward_json`); the owning service validates its own request bodies. If the gateway needs a shared shape (for example a response it aggregates), put a small contract module in `libs/` and import that.
2. Remove the service packages from `gateway/api/pyproject.toml` and update `uv.lock`.
3. Add a lint gate that fails on any import of a service package from `gateway/api/src` (import-linter contract or ruff `flake8-tidy-imports` banned-api), wired into `make lint`.
4. Coordinate with TASK-0589 (soundscape proxy): if 0589 is not done, do the soundscape part here.

## Frontdoor Blackbox Test Plan
- A malformed request body through each proxy returns the owning service's 422 (validation lives there).
- The lint gate fails on a deliberately added service import (show it once in the report, then remove it).

## Definition of Done
- `gateway/api/src` imports no service package, and `make lint` enforces it.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high
- Source audits: `drafts/round3-notes.md`
