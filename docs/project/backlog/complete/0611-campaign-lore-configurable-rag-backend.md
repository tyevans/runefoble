---
id: '0611'
title: Campaign Lore Configurable Hybrid RAG Backend Replaces Hardwired In-Memory Fakes
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0011
- ADR-0014
governing_prds:
- PRD-0007
governing_stories:
- US-0036
target_release: 0.9.0
severity: high
source_audits:
- w2-campaign-lore.md
---

# TASK-0611: Campaign Lore Configurable Hybrid RAG Backend Replaces Hardwired In-Memory Fakes

## Status
Complete

## Summary
Campaign lore retrieval is built on redstring's in-memory and fake providers. No setting selects a real backend. Entity extraction is a regex heuristic that records its result as an LLM extraction with confidence 1.0. This task adds a configured backend selection (graph, vector, chunk, embedding, LLM) with production adapters and keeps the fakes only as test fixtures.

## Problem Statement
- `services/campaign_lore/src/campaign_lore/retrieval.py:29-37`: `FakeEmbeddingProvider`, `InMemoryGraphStore`, `InMemoryVectorStore`, `InMemoryChunkStore` are hard-wired in `LoreRetrievalEngine.__init__`.
- `extraction.py:109-120` and `185-186`: `WorldbuildingLlmProvider` is a regex heuristic. Its model `runefoble/worldbuilding-ner-v1` is never called.
- redstring ships `PgVectorStore`, `PostgresChunkStore`, `Neo4jGraphStore`, and LangChain providers. None is used.
- `retrieval.py:98-115`: `consolidate_alias` records `ExtractionMethod.LLM` at confidence 1.0 for regex data.

Source: `.audit/reports/w2-campaign-lore.md` F6. Related but separate: TASK-0469 (proposed) RAG blackbox tests; TASK-0466 (proposed) lore tools.

## Documentation & Architecture Review
- `docs/how-to/index-campaign-lore-with-redstring.md`: describes the ingest and query path. Update the backend section.
- `docs/reference/platform-services.md`: lists platform services and env vars. Add the lore backend settings.
- ADR-0011: aggregates keep state through eventsource-py. This task does not change aggregates (see w2-campaign-lore F9 for that, a separate task).
- Hard Invariant 4: install redstring extras through the UV workspace only.

## Product & User Story References
- `docs/project/product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md`
- `docs/project/user_stories/accepted/us-0036-rag-indexed-campaign-worldbuilding-lore.md`

## Detailed Specification & Implementation Plan
1. Add `LoreBackendSettings` to `libs/runefoble_platform/src/runefoble_platform/config.py` with fields `graph`, `vector`, `chunk`, `embedding`, `llm` (each a literal choice; `memory` allowed only for tests).
2. Add factory functions in `services/campaign_lore/src/campaign_lore/retrieval_factory.py` that build each port from settings.
3. `LoreRetrievalEngine` receives its ports through the constructor. Remove the default fakes.
4. Production defaults: Postgres/pgvector for vectors and chunks, Neo4j or redstring's graph store for the graph, and a configured embedding provider. Start-up fails if a configured backend is unreachable.
5. Extraction uses the configured LLM provider. When set to the heuristic, record `ExtractionMethod.HEURISTIC`, not `LLM`.
6. Document the settings in the platform services reference.

## Frontdoor Blackbox Test Plan
- Before fix: ingest a document through the lore ingest route, then query. The result depends on in-process fakes; a restart loses it (test fails when the service restarts with the same database).
- After fix: a document ingested before a service restart is returned by the query route after restart, with the Postgres backend configured in the test.
- After fix: an alias from the heuristic extractor is recorded with method `heuristic`.
- After fix: start-up with an unreachable configured backend exits with an error.

## Definition of Done
1. No redstring fake or in-memory store is constructed in `services/campaign_lore/src`.
2. Factory and settings in place. Files under 500 lines.
3. Blackbox tests pass. `uv run pytest services/campaign_lore` passes.
4. Ruff check and format pass.
5. How-to and platform services reference updated. `CHANGELOG.md` `[Unreleased]` entry added.

## Orchestrator Decisions (2026-11-17, after worker block report)
The first worker stopped with valid questions. These decisions narrow and replace the scope above where they conflict:
1. Use `redstring.ExtractionMethod.PATTERN` for regex extraction. Do not name a `HEURISTIC` method. Rename `WorldbuildingLlmProvider` to a name that says it is pattern-based, and update all call sites and exports. Remove the `HybridLoreEngine` alias (`retrieval.py:193-194`).
2. Do not add Neo4j. The event store is the source of truth (ADR-0011, ADR-0015). Rebuild the entity graph and the document metadata (title, `is_secret`) as a projection from the lore aggregate events at application start-up, in a FastAPI lifespan hook. Do not build the engine at import time. A restart must keep search results and secrecy filtering intact.
3. Scope of this task: settings, factory, lifespan, and the event-replayed projection for graph and metadata. Vector storage and the embedding provider move to a separate task (pgvector store and an OpenAI-compatible embedding-provider port). Until that task lands, the current in-process vector index is rebuilt from the replayed documents at start-up, and the docs say so.
4. Tests: use the existing PostgreSQL test fixture pattern in the repo (search `tests/` and `services/game_session/tests` for the Postgres-backed tests) for the restart test. Restart means: build a new app instance on the same event store, then query through HTTP.
5. Read `spicedb_token` from settings directly (`dependencies.py:75`), with no `"secret"` default.
