---
id: '0670'
title: Campaign Lore pgvector Store and OpenAI-Compatible Embedding Provider Port
status: Complete
created: 2026-11-17
dependencies:
- TASK-0611
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0011
- ADR-0015
governing_prds:
- PRD-0007
governing_stories:
- US-0036
target_release: 0.9.0
severity: high
source_audits:
- w2-campaign-lore.md
---

# TASK-0670: Campaign Lore pgvector Store and OpenAI-Compatible Embedding Provider Port

## Status
Complete

## Summary
Campaign lore vector search uses an in-process vector index and a fake embedding provider. This task adds a PostgreSQL pgvector store and an embedding-provider port with an OpenAI-compatible HTTP adapter. The in-process index is removed from production code.

## Problem Statement
- TASK-0611 moved the entity graph and document metadata to an event-replayed projection. The vector index stays in process and is rebuilt from replayed documents at start-up.
- `services/campaign_lore/src/campaign_lore/retrieval.py`: the embedding provider is the redstring fake. Similarity results do not reflect meaning.
- No setting selects an embedding endpoint. redstring ships `PgVectorStore`, but nothing uses it.

## Documentation & Architecture Review
- ADR-0015: deployed services fail fast when a configured backend is unreachable. No fallback to fakes.
- `docs/how-to/index-campaign-lore-with-redstring.md` must describe the pgvector store and the embedding settings.

## Product & User Story References
- PRD-0007, US-0036: the DM queries lore and gets relevant results.

## Detailed Specification & Implementation Plan
1. Add an `EmbeddingProvider` port in campaign_lore. Add an adapter that calls an OpenAI-compatible `/v1/embeddings` endpoint (settings: base URL, model, dimensions, API key from a K8s Secret).
2. Add `vector: pgvector` to the lore backend settings. Use redstring `PgVectorStore` with the platform PostgreSQL DSN. Create the extension and table at start-up.
3. The fake embedding provider and in-memory vector store move to `tests/helpers`. Production settings reject `memory`.
4. Start-up fails with a clear error if PostgreSQL or the embedding endpoint is unreachable.
5. Helm: add the embedding settings and Secret reference to the campaign-lore values. Use the pgvector Postgres image or enable the extension.

## Frontdoor Blackbox Test Plan
- Ingest two documents through `POST` lore routes. Query with a phrase close to one document. The close document ranks first (test embedding server at the network boundary returns fixed vectors).
- Restart the app on the same PostgreSQL fixture. The same query returns the same ranking with no re-ingest.
- Point the embedding URL at a closed port. Start-up fails.

## Definition of Done
- Tests above pass. No fake embedding or in-memory vector store in production code.
- Docs and Helm values updated. CHANGELOG line given to the orchestrator.
