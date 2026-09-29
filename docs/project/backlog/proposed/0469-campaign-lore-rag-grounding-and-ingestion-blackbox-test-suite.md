---
id: '0469'
title: Campaign Lore RAG Grounding and Ingestion Blackbox Test Suite
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0466
- TASK-0467
- TASK-0468
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0007
governing_prds:
- PRD-0001
- PRD-0007
governing_stories:
- US-0001
- US-0036
target_release: 0.9.0
---

# TASK-0469: Campaign Lore RAG Grounding and Ingestion Blackbox Test Suite

## Status
Proposed

## Summary
Implement a comprehensive end-to-end blackbox test suite (`tests/test_blackbox_campaign_lore_rag_and_grounding.py`) verifying the complete Campaign Lore knowledge lifecycle per PRD-0007: ingesting worldbuilding documents through the Gateway API frontdoor, extracting entities and relationships, consolidating aliases, verifying FastMCP `query_campaign_lore` and `resolve_lore_alias` tool execution, testing The Watcher speech-to-intent narrative grounding, and confirming SpiceDB Zanzibar shields secret lore (`is_secret=True`) from unauthorized player queries.

## Problem Statement
While individual modules in `campaign_lore` have localized unit tests, the system lacks an end-to-end blackbox integration suite testing the full chain: Gateway API ingestion -> redstring graph extraction -> FastMCP tool invocation -> The Watcher narrative grounding -> Zanzibar permission enforcement. Without this suite, regressions in graph traversal or secret leakage cannot be detected prior to production deployment.

## Governing Architecture & ADRs
- **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: Blackbox assertion of Zanzibar permission boundaries between DMs and players.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Standard test suite execution under `uv run pytest`.
- **ADR-0007: Domain-Driven Design Architecture**: Blackbox testing through public HTTP routes and FastMCP tools without backdoor database manipulation.

## Product & User Story References
- [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- [`prd-0007-campaign-worldbuilding-lore-and-rag-engine.md`](../../product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md)
- [`us-0001-player-commands-board-via-voice.md`](../../user_stories/accepted/us-0001-player-commands-board-via-voice.md)
- [`us-0036-rag-indexed-campaign-worldbuilding-lore.md`](../../user_stories/accepted/us-0036-rag-indexed-campaign-worldbuilding-lore.md)

## Scope of Work
1. **Gateway Document Ingestion Flow**:
   - Ingest sample worldbuilding lore documents with public and secret sections via `POST /api/v1/campaigns/{campaign_id}/lore/documents`.
   - Assert response returns extracted entity count, relationship count, and indexed chunk status.
2. **Alias Consolidation & Resolution**:
   - Post an alias consolidation request (`POST /api/v1/campaigns/{campaign_id}/lore/aliases/consolidate`) merging an alias into a canonical entity.
   - Assert `GET /api/v1/campaigns/{campaign_id}/lore/aliases/resolve` resolves the alias to the canonical name.
3. **FastMCP Tool Execution**:
   - Call FastMCP `query_campaign_lore` and assert hybrid search returns relevant document snippets and entity relations.
   - Call FastMCP `resolve_lore_alias` and assert canonical entity resolution.
4. **The Watcher RAG Grounding Verification**:
   - Dispatch speech-to-intent queries inquiring about lore concepts.
   - Assert The Watcher intent resolution incorporates retrieved lore context into the generated narrative response.
5. **SpiceDB Zanzibar Secret Protection**:
   - Execute query with player credentials and assert secret documents are omitted from results.
   - Execute query with DM credentials and assert secret documents are included.

## Definition of Done
1. `tests/test_blackbox_campaign_lore_rag_and_grounding.py` implemented strictly < 250 lines per Hard Invariant 6.
2. All 5 test scenarios execute and pass cleanly via `uv run pytest tests/test_blackbox_campaign_lore_rag_and_grounding.py`.
3. Verifies zero leakage of `is_secret=True` lore to unprivileged player roles.
4. Test suite follows blackbox TDD with frontdoor setup per Hard Invariant 7.
5. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
