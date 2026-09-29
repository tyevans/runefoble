---
id: '0466'
title: FastMCP Campaign Lore RAG Tools and The Watcher Intent Grounding
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0005
- TASK-0047
- TASK-0448
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0009
governing_prds:
- PRD-0001
- PRD-0007
governing_stories:
- US-0001
- US-0036
target_release: 0.9.0
---

# TASK-0466: FastMCP Campaign Lore RAG Tools and The Watcher Intent Grounding

## Status
Proposed

## Summary
Expose Model Context Protocol (FastMCP) tools for campaign lore knowledge graph traversal and hybrid RAG retrieval (`query_campaign_lore`, `resolve_lore_alias`, `inspect_lore_entity`) in `gateway/mcp/src/gateway_mcp/tools/lore.py`. Integrate The Watcher AI engine (`services/the_watcher`) to query campaign lore indices when evaluating narrative dialogue, player rumors, and in-world inquiries, ensuring answers reflect custom DM worldbuilding without narrative hallucinations.

## Problem Statement
Currently, `gateway/mcp` provides FastMCP tools for board state, character sheet, compendium rules, and dice rolling, but completely lacks tools to query campaign worldbuilding lore, entity relationships, or alias clusters managed by `services/campaign_lore`. Consequently, when autonomous or co-pilot LLMs (The Watcher) process speech intents or generate NPC dialogue, they have no direct access to custom DM lorebooks or knowledge graphs, risking hallucinations or conflicting lore statements per PRD-0007.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular tool registration in `gateway/mcp/src/gateway_mcp/tools/lore.py`.
- **ADR-0007: Domain-Driven Design Architecture**: Clean client boundary between FastMCP gateway, The Watcher copilot engine, and Campaign Lore retrieval services.
- **ADR-0009: Model Context Protocol Integration**: Standard FastMCP tool interfaces with typed schemas and JSON output payloads.

## Product & User Story References
- [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- [`prd-0007-campaign-worldbuilding-lore-and-rag-engine.md`](../../product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md)
- [`us-0001-player-commands-board-via-voice.md`](../../user_stories/accepted/us-0001-player-commands-board-via-voice.md)
- [`us-0036-rag-indexed-campaign-worldbuilding-lore.md`](../../user_stories/accepted/us-0036-rag-indexed-campaign-worldbuilding-lore.md)

## Scope of Work
1. **FastMCP Lore Tools Implementation (`gateway/mcp/src/gateway_mcp/tools/lore.py`)**:
   - Register `query_campaign_lore(campaign_id: str, query: str, top_k: int = 5, include_secrets: bool = False)` calling `campaign_lore` `/api/v1/lore/search`.
   - Register `resolve_lore_alias(campaign_id: str, name: str)` calling `/api/v1/lore/aliases/resolve`.
   - Register `inspect_lore_entity(campaign_id: str, entity_name: str)` returning entity node attributes and first-degree graph relations.
2. **Tool Aggregator Export (`gateway/mcp/src/gateway_mcp/tools/__init__.py`)**:
   - Export and register lore tools within the FastMCP server tool registry alongside board, character, and compendium tools.
3. **The Watcher RAG Knowledge Ingestion Client (`services/the_watcher/src/the_watcher/lore_client.py`)**:
   - Implement asynchronous client querying `campaign_lore` retrieval endpoints with configurable timeout (<= 150ms).
   - Inject relevant retrieved facts and entity lore into The Watcher intent prompting context.
4. **Context Injection in Copilot & Intent Engine (`services/the_watcher/src/the_watcher/copilot.py`)**:
   - When players ask in-character questions or probe rumors, query campaign lore and provide grounding context snippets to the DM copilot suggestions.

## Definition of Done
1. `gateway/mcp/src/gateway_mcp/tools/lore.py` implemented and strictly < 130 lines per Hard Invariant 6.
2. FastMCP server registers `query_campaign_lore`, `resolve_lore_alias`, and `inspect_lore_entity` tools.
3. The Watcher lore client successfully retrieves context snippets from `services/campaign_lore` within 150ms.
4. Unit tests in `gateway/mcp/tests/` and `services/the_watcher/tests/` verify tool registration and query dispatch.
5. All code passes `uv run ruff check .` and `uv run ruff format --check .`.
