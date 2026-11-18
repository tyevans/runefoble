---
id: '0612'
title: Asset Forge Silo Upload Fails Closed and Asset Index Is Durable
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0005
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0009
governing_stories:
- US-0038
- US-0049
target_release: 0.9.0
---

# TASK-0612: Asset Forge Silo Upload Fails Closed and Asset Index Is Durable

## Status
Complete

## Summary
Asset uploads report success after a failed Silo write. The bytes go to an in-memory store and the caller gets a URL that does not exist after restart. This task removes the in-memory fallback from the production upload path. A failed Silo write returns a 5xx and records nothing. The asset index moves to a durable store.

## Problem Statement
- `libs/runefoble_platform/src/runefoble_platform/storage.py` `upload_asset` (about lines 137-205): a remote PUT has a 1.5 s timeout. Failures are logged at DEBUG. A non-2xx response is a WARNING. The code then stores bytes in `self._memory_store` and metadata in `self._asset_index`, and returns a URL.
- `get_asset_by_id` reads only `_asset_index`. It is used by `routers/battlemap.py`, `token.py`, and `wardrobe.py` in asset_forge.
- There is no setting that disables the fallback.
- `w1-libs.md` F6 describes the same `storage.py` fallback (lines 137-160).

Sources: `.audit/reports/w2-asset-forge.md` F1; `.audit/reports/w1-libs.md` F6 (storage part).

## Documentation & Architecture Review
- `docs/reference/platform-services.md`: Silo endpoint and bucket settings.
- `docs/how-to/forge-procedural-battlemaps-and-tokens.md`: describes the returned URL. Update the failure behaviour.
- TASK-0497 (refined, shims) edits asset_forge files. Coordinate the merge.
- ADR-0007: the asset index is a domain record. Store it through the event store or Postgres, not process memory.

## Product & User Story References
- `docs/project/product/accepted/prd-0009-procedural-battlemap-and-token-asset-generation.md`
- `docs/project/user_stories/accepted/us-0038-generative-procedural-battlemaps-and-tokens.md`

## Detailed Specification & Implementation Plan
1. In `storage.py`, `upload_asset` raises `AssetStorageError` on any Silo failure. Remove the memory fallback from the production path.
2. The memory store stays only as an injected test double (`set_storage`), not as a default.
3. Record the asset index only after a successful Silo write. Persist it as an event through eventsource-py (asset aggregate) so GET works after restart and across replicas.
4. The forge routes map `AssetStorageError` to HTTP 503.
5. The GET routes read the index through the aggregate repository.
6. Update the platform services and forge how-to docs.

## Frontdoor Blackbox Test Plan
- Before fix: POST a battlemap forge request with Silo unreachable. Response 200 with a URL. GET of that URL's id returns 200 only from memory (test fails after restart).
- After fix: the same request returns 503 and no asset id is created (GET of any returned id is 404).
- After fix: with Silo available (test double at its HTTP boundary), the asset GET works after the service restarts.

## Definition of Done
1. `upload_asset` has no fallback to `_memory_store` in production code.
2. Asset index durable. Files under 500 lines.
3. Blackbox tests pass. `uv run pytest services/asset_forge libs/runefoble_platform` passes.
4. Ruff check and format pass.
5. Docs and `CHANGELOG.md` `[Unreleased]` updated.

## Audit Provenance

- Severity: high
- Source audits: `w2-asset-forge.md`, `w1-libs.md`
