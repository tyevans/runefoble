---
id: 0047
title: Campaign Lore Knowledge Base & redstring RAG Microservice
status: Proposed
created: 2026-09-25
dependencies: [TASK-0001, TASK-0008, TASK-0033]
governing_adrs: [ADR-0001, ADR-0006, ADR-0007, ADR-0011]
target_release: 0.3.0
---

# TASK-0047: Campaign Lore Knowledge Base & redstring RAG Microservice

## Status
Proposed

## Summary
Scaffold a new bounded context microservice `services/campaign_lore` powered by `redstring` (`tyevans/redstring` on GitHub / PyPI) to extract knowledge graphs from worldbuilding docs, perform alias consolidation, and serve hybrid RAG queries (graph + vector + BM25) to The Watcher.

## Problem Statement
DMs spend 8+ hours preparing lore, but in-session AI intent parsing and dialogue have no grounding in the DM's custom world history and faction relationships, resulting in hallucinations or requiring constant manual DM correction.

## Scope of Work
1. **redstring Integration**: Add `redstring[pgvector,redis,llm]` to UV monorepo workspace.
2. **Knowledge Graph Extraction**: Use `redstring.build_graph` with `SourceDocument` to extract entities, relationships, and alias consolidation clusters (e.g. mapping aliases to single nodes).
3. **Event-Sourced Graph Projections**: Leverage `redstring`'s native `eventsource-py` event-driven architecture to store extraction events and project graphs into Postgres / pgvector.
4. **Hybrid Search RAG Endpoint**: Expose `/api/v1/lore/search` combining `redstring` graph neighbor walks, dense vector embeddings, and BM25 lexical keyword matching.
5. **SpiceDB Zanzibar Authorization**: Enforce DM-only secret lore filtering vs. public player codex visibility.

## Acceptance Criteria
1. Lore document ingestion uses `redstring` to extract entities, relationships, and consolidated alias clusters.
2. Hybrid search endpoint resolves queries in under 50ms using BM25, embeddings, and graph traversal.
3. Secret DM lore entries are strictly filtered from player-facing queries via SpiceDB permissions.
4. Full blackbox tests verifying document ingestion, graph queries, and CloudEvents emission.
