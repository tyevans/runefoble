---
id: '0735'
title: Lore and Compendium Share One Retrieval Wiring Module With a Start-Up Probe
status: Refined
created: 2026-11-17
dependencies:
- TASK-0244
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0007
- PRD-0008
governing_stories:
- US-0036
- US-0037
target_bc: core
target_release: 0.9.0
---
# TASK-0735: Lore and Compendium Share One Retrieval Wiring Module With a Start-Up Probe

## Status
Refined. Found by the refactor audit round refactor-r1 and checked against the code on 2026-11-17.

## Summary
campaign_lore and rules_compendium each build the embedding provider, chunk store, and retriever in their own style. Only lore probes the embedding endpoint at start-up.

## Problem Statement
- `services/campaign_lore/src/campaign_lore/retrieval_factory.py:20-33` builds the provider with a start-up probe, builds a PgVector store with an inline DSN rewrite (`:42`), and selects backends with `match` and `assert_never`.
- `services/rules_compendium/src/rules_compendium/retrieval_factory.py:20-31` builds the same provider through `build_adapter`, with no probe and no PgVector path.
- Both engines build `redstring.ChunkRetriever` and `InMemoryChunkStore` (lore `retrieval.py:44-51`, compendium `retrieval.py:56-74`).
- `rules_compendium/main.py:28` builds its settings inside `lifespan`. Lore receives settings as arguments.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- `docs/reference/embedding-providers.md`, `docs/how-to/add-an-engine-port-adapter.md`. TASK-0244 splits compendium `retrieval.py`: run after it, and correct its compatibility wording first (see the index).

## Product & User Story References
- PRD-0007
- PRD-0008
- US-0036
- US-0037

## Detailed Specification & Implementation Plan
1. Add `libs/runefoble_embeddings` functions (or a sibling lib): `build_embedding_port(mode, endpoint)`, `probe_embedding_port(provider)`, `build_chunk_store(mode, dimension)`, and `build_pgvector_store(database_url, dimension, table)` with the DSN rewrite in one place.
2. Both factories shrink and call these. Compendium takes its settings through `create_app` and probes at start-up.
3. Update call sites directly. Add no alias.

## Frontdoor Blackbox Test Plan
- Start each service with an unreachable embedding endpoint. Start-up fails with the same error class in both.
- Existing lore and compendium blackbox suites pass unchanged.

## Definition of Done
- Neither factory builds a PgVector DSN or a probe itself.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: low
- Source audits: `lore-rules-analytics-sound.md (F3)`
