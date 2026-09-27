---
id: '0047'
title: Campaign Lore Knowledge Base & redstring RAG Microservice
status: Complete
created: 2026-09-25
dependencies:
- TASK-0001
- TASK-0008
- TASK-0033
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0006
- ADR-0007
- ADR-0009
- ADR-0011
target_release: 0.3.0
pr_url: https://github.com/tyevans/runefoble/pull/45
governing_prds:
- PRD-0007
governing_stories:
- US-0018
- US-0036
---
# TASK-0047: Campaign Lore Knowledge Base & redstring RAG Microservice

## Status
Refined

## Summary
Scaffold a new bounded context microservice `services/campaign_lore` powered by `redstring` (`tyevans/redstring` on GitHub / PyPI) to extract knowledge graphs from worldbuilding docs, perform alias consolidation, and serve hybrid RAG queries (graph + vector + BM25) to The Watcher AI DM engine.

## Problem Statement
DMs spend 8+ hours preparing lore, but in-session AI intent parsing and dialogue have no grounding in the DM's custom world history and faction relationships, resulting in hallucinations or requiring constant manual DM correction.

## PRD & User Story Alignment
- **Governing PRD**: [`prd-0007-campaign-worldbuilding-lore-and-rag-engine.md`](../../product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md)
- **User Story**: [`us-0036-rag-indexed-campaign-worldbuilding-lore.md`](../../user_stories/accepted/us-0036-rag-indexed-campaign-worldbuilding-lore.md)

## Governing Architecture & ADRs
- **ADR-0001**: SpiceDB Zanzibar Object-Level Authorization (DM-only secret lore vs player-visible codex filtering).
- **ADR-0003**: UV Monorepo Workspace for Python Bounded Contexts.
- **ADR-0006**: Redis Streams Event Bus Infrastructure.
- **ADR-0007**: API Gateway Architecture and FastMCP routing.
- **ADR-0009**: Code Quality and Linting with Ruff (< 500 lines per file).
- **ADR-0011**: eventsource-py Core Event Sourcing Architecture.

## Proposed Architecture & Technical Plan
1. **UV Monorepo Integration (`services/campaign_lore`)**:
   - Create `services/campaign_lore` bounded context package added to root `pyproject.toml` workspace.
   - Add `redstring[redis,llm]` dependency to manage extraction, graph entities, and hybrid retrieval.
2. **Event-Sourced Lore Aggregate (`services/campaign_lore/src/campaign_lore/aggregate.py`)**:
   - `LoreDocumentAggregate` inheriting from `eventsource-py` `DeclarativeAggregate`.
   - Domain events: `LoreDocumentIngested`, `EntitiesExtracted`, `AliasesConsolidated`.
3. **Hybrid Retrieval Engine (`services/campaign_lore/src/campaign_lore/retrieval.py`)**:
   - Ingestion handler that builds graph projections via `redstring.build_graph`.
   - Hybrid search combining graph neighbor walks, dense embeddings, and BM25 lexical keyword scoring.
4. **Public HTTP Frontdoor API (`services/campaign_lore/src/campaign_lore/main.py` & routers)**:
   - `POST /api/v1/lore/documents`: Ingest markdown/text worldbuilding documents with campaign ID and visibility flag.
   - `POST /api/v1/lore/search`: Execute hybrid search query parameterized by campaign ID, query string, and caller identity.
   - Enforce SpiceDB Zanzibar relations: filter out secret DM-only lore for standard player identities.

## INVEST Criteria Evaluation
- **Independent (I)**: Self-contained bounded context with clean public HTTP frontdoors and event-driven Redis Streams subscriptions.
- **Negotiable (N)**: Hybrid search weight ratios (graph vs vector vs BM25) can be fine-tuned without modifying endpoint contracts.
- **Valuable (V)**: Eliminates AI DM hallucinations and grounds NPC interactions in custom campaign canon.
- **Estimable (E)**: Built on standard `redstring` and `eventsource-py` primitives.
- **Small (S)**: Confined to service scaffolding and core RAG routers; every file < 300 lines.
- **Testable (T)**: Tested strictly via blackbox HTTP calls to document ingestion and search endpoints.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Bounded Context Scaffolding**:
   - `services/campaign_lore` package initialized and integrated into root UV workspace.
2. **Frontdoor Blackbox Test Suite**:
   - New suite in `tests/test_blackbox_campaign_lore_rag.py` exercising:
     - Document ingestion via `POST /api/v1/lore/documents`.
     - Alias consolidation validation (e.g. "The Silver Knight" resolves to "Sir Gareth").
     - Sub-50ms hybrid retrieval via `POST /api/v1/lore/search`.
     - SpiceDB authorization filtering verifying players cannot retrieve DM secret lore.
3. **Hard Invariant Compliance**:
   - Zero files exceeding 500 lines (Hard Invariant 6).
   - Domain events inherit from `BaseRunefobleEvent` and state transitions use `eventsource-py` (Hard Invariant 2).
   - OpenAPI specifications exposed at `/openapi.json` (Hard Invariant 5).
4. **Automated Quality Gates**:
   - `uv run pytest tests/test_blackbox_campaign_lore_rag.py` passes 100%.
   - `uv run ruff check services/campaign_lore` and `uv run ruff format --check services/campaign_lore` pass cleanly.
