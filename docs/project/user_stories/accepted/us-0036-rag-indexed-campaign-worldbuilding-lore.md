---
id: 0036
title: Campaign Worldbuilding Knowledge Graphs & redstring RAG Retrieval
status: Accepted
created: 2026-09-25
---

# US-0036 — Campaign Worldbuilding Knowledge Graphs & redstring RAG Retrieval

## User Story

**As a** Dungeon Master crafting complex homebrew campaigns (Evelyn),  
**I want** my worldbuilding documents, NPC relationship graphs, and faction histories indexed through `tyevans/redstring`,  
**So that** The Watcher queries unified knowledge graphs, embeddings, and BM25 search to incorporate canon-compliant lore and NPC motivations into real-time dialogue without hallucinations.

## Acceptance Criteria

1. **redstring Knowledge Graph Ingestion**: Ingests campaign documents with `redstring`, extracting entities and folding relationships into `eventsource-py` event-sourced graph projections.
2. **Entity Alias Consolidation**: Merges synonymous character titles and aliases (e.g. "The Silver Knight" = "Sir Gareth") into single canonical nodes via `redstring`.
3. **Hybrid Search Retrieval**: Resolves player lore queries in under 50ms using `redstring` hybrid search combining graph neighbor walks, dense vector embeddings, and BM25 lexical keyword matching.
