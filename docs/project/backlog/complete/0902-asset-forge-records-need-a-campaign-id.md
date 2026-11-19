---
id: '0902'
title: Asset Forge Records Need a Campaign Id, Not a Random One
status: Complete
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: asset_forge
target_release: 0.9.0
---

# TASK-0902: Asset Forge Records Need a Campaign Id, Not a Random One

## Status

Complete

## Summary

When a forge request has no campaign id, asset_forge saves the forge record in an aggregate with a new random id. No route can find that aggregate again, so the record is lost. The identifier policy (ADR-0015, `docs/reference/identifiers-and-uuid-policy.md`) does not allow a random substitute id.

## Problem Statement

- `services/asset_forge/src/asset_forge/routers/battlemap.py:101`: `agg_id = request.campaign_id or uuid4()`.
- `services/asset_forge/src/asset_forge/routers/token.py:79`: the same pattern.
- `services/asset_forge/src/asset_forge/routers/print_forge.py:49`: `target_id = agg_id or uuid4()`.

## Documentation & Architecture Review

- `docs/reference/identifiers-and-uuid-policy.md`: no random substitute ids. Server-assigned ids are only for create points that return the id.
- `docs/how-to/forge-procedural-battlemaps-and-tokens.md`.

## Product & User Story References

None. Data integrity.

## Detailed Specification & Implementation Plan

1. Find which forge routes accept a request without a campaign (check the gateway campaign forge routes from TASK-0787).
2. If every caller passes a campaign: make `campaign_id` required and answer 422 when it is missing. Delete the `or uuid4()` code.
3. If a campaign-free forge is a real use case: do not save a forge record for it, and say so in the how-to. Do not invent an id.
4. Update the how-to and the API reference.

## Frontdoor Blackbox Test Plan

- A forge request without `campaign_id` answers 422 (or, for option 3, publishes and saves no forge record), through the public route.
- A forge request with a campaign saves the record, and the campaign asset list shows it.

## Definition of Done

- Tests above pass. No `or uuid4()` in asset_forge routers. Docs and CHANGELOG `Fixed` entry.

## Audit Provenance

- Severity: medium
- Source audits: .audit/work/0731.md
