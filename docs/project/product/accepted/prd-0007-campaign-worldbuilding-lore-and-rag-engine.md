---
id: 0007
title: Campaign Worldbuilding Lore & redstring RAG Engine
status: Accepted
created: 2026-09-25
---

# PRD-0007 — Campaign Worldbuilding Lore & redstring RAG Engine

## Who this is for

Human Dungeon Masters (Evelyn) managing homebrew campaigns, players discovering secrets during play, and autonomous AI DMs (The Watcher) requiring accurate campaign continuity.

## What the person cannot do today

Currently, campaign lore lives in external notes, notebooks, or memory. In-session AI intent parsing and narrative generation have no access to the DM's custom world history, faction rivalries, NPC motivations, or secret plot hooks, leading to narrative hallucination or constant manual correction.

## What good looks like

- **Knowledge Graphs & Consolidation via redstring**: Ingestion pipeline powered by `redstring` (`tyevans/redstring` on GitHub / PyPI). Documents are processed into knowledge graphs with automatic entity extraction and alias consolidation (e.g. mapping "Aurelia Vane", "Lady Aurelia", and "The Iron Duchess" to a single canonical entity node).
- **Event-Sourced Graph Storage**: Extracted facts are modeled as events and folded into graph projections via `eventsource-py`, ensuring extraction stores can be rebuilt or replayed as prompts evolve.
- **Hybrid Multi-Modal Search**: Sub-50ms hybrid retrieval combining graph neighbor traversal, dense vector embeddings (`pgvector`), and BM25 lexical keyword matching provided by `redstring`.
- **RAG-Grounded Watcher Adjudication**: When players ask questions or probe rumors in character, The Watcher queries `redstring` hybrid indices to deliver canon-compliant dialogue and clues without hallucinating.
- **Player Codex & Discovery Journal**: Secrets and lore unlocked by players are projected into a public player codex, while private DM secrets remain shielded behind Zanzibar authorization.

## What this does not do

- It does not force a specific campaign setting; users can build homebrew worlds or import open SRD lore.
- It does not overwrite player character backstories without player consent.

## What it costs at scale

Vector embeddings and text chunk indexing require asynchronous worker processing and storage in pgvector / Postgres and Redis caching.

## Checkable Outcomes

1. Lore documents ingested through `redstring` extract entities, relationships, and alias consolidation clusters.
2. The Watcher queries `redstring` hybrid search (BM25 + vector embeddings + graph traversal) during dialogue and intent generation.
3. Players can inspect discovered lore entries in an interactive in-game codex without seeing DM-only secrets.

## Linked User Stories
- [`US-0018: Secret DM Traps, Map Switching, and Stage Triggers`](../../user_stories/accepted/us-0018-secret-dm-traps-map-switching-and-stage-triggers.md)
- [`US-0019: Ad-Hoc Ephemeral NPC Spawning and Scene-Wide Conditions`](../../user_stories/accepted/us-0019-ad-hoc-ephemeral-npc-spawning-and-scene-conditions.md)
- [`US-0036: Campaign Worldbuilding Knowledge Graphs & redstring RAG Retrieval`](../../user_stories/accepted/us-0036-rag-indexed-campaign-worldbuilding-lore.md)

## Implementing Backlog Tasks
- [`TASK-0047: Campaign Lore Knowledge Base & redstring RAG Microservice`](../../backlog/complete/0047-campaign-lore-rag-knowledge-base-bc.md)
- [`TASK-0089: Campaign Lore Extraction, Embeddings, and Hybrid Retrieval Modular Decomposition`](../../backlog/complete/0089-campaign-lore-retrieval-and-extractor-modular-decomposition.md)
- [`TASK-0466: FastMCP Campaign Lore RAG Tools and The Watcher Intent Grounding`](../../backlog/proposed/0466-fastmcp-campaign-lore-rag-tools-and-watcher-intent-grounding.md)
- [`TASK-0467: Gateway Campaign Lore Documents and Alias API Routing & Zanzibar Proxy`](../../backlog/proposed/0467-gateway-campaign-lore-documents-and-alias-api-proxy.md)
- [`TASK-0468: App Shell Campaign Lore Document Uploader and Alias Manager Microfrontend`](../../backlog/proposed/0468-app-shell-campaign-lore-document-uploader-and-alias-manager.md)
- [`TASK-0469: Campaign Lore RAG Grounding and Ingestion Blackbox Test Suite`](../../backlog/proposed/0469-campaign-lore-rag-grounding-and-ingestion-blackbox-test-suite.md)

