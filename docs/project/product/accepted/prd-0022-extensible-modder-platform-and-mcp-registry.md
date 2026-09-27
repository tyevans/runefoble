---
id: '0022'
title: Extensible Modder Platform, Universal VTT Asset Bridge & FastMCP Tool Registry
status: Accepted
created: 2026-09-26
---

# PRD-0022 — Extensible Modder Platform, Universal VTT Asset Bridge & FastMCP Tool Registry

## Who this is for

Developer modders (like Alex the Developer / Plugin Modder) and Game Masters (like Evelyn) who want to extend Runefoble with custom Discord bots, external AI agents, homebrew rulesets, and community battlemap imports.

## What the person cannot do today

- Commercial virtual tabletops lock users into proprietary walled gardens with closed APIs, requiring brittle DOM scraping or reverse-engineered network packets to build custom tools.
- Developers cannot easily hook external Large Language Models (Claude, Gemini, local Ollama models) into live tabletop state to build specialized assistants or automated NPCs.
- DMs with extensive libraries of Universal VTT (`.dd2vtt`, `.uvtt`) maps and custom homebrew rulesets face tedious manual recreation of walls, lights, and tile scripts.
- Community extensions cannot mount custom web components into the platform without modifying core application source code.

## What good looks like

1. **Standardized FastMCP Tool & Resource Gateway**:
   - Model Context Protocol server exposing robust tabletop tools (`roll_dice`, `inspect_tactical_board`, `move_board_token`, `query_lore`, `modify_character_sheet`) to external LLM agents.
   - Comprehensive MCP resource endpoints streaming live session transcripts and initiative states.
2. **Universal VTT Asset Bridge & Importer**:
   - Importer supporting standard Universal VTT (`.dd2vtt`, `.uvtt`) format files, automatically parsing image layers, grid scale, line-of-sight wall occlusions, doors, and ambient light sources.
   - Scriptable grid tile triggers allowing homebrew creators to bind custom traps, teleporters, and scene triggers directly to map tiles.
3. **Runtime Extension Slots & Hot-Reloading MCP Registry**:
   - Extensible Lit Web Component mounting slots in the frontend shell for community custom panels, character sheet widgets, and soundboard modules.
   - Dynamic plugin registration allowing developers to register and hot-reload custom MCP tools and event listeners without server restarts.
4. **Redis Streams Domain Event Webhooks**:
   - High-throughput event subscription gateway allowing external bots (e.g. Discord dice-bot, Twitch stream alerts) to consume game events in real time.

## What this does not do

- It does not bypass Zanzibar SpiceDB authorization; third-party MCP agents and plugins are strictly subject to tenant isolation and campaign permission scopes.
- It does not allow unauthenticated or unsandboxed code execution on server nodes.

## Checkable Outcomes

1. FastMCP server executes tool invocations and returns structured JSON responses in under 50ms.
2. Universal VTT importer parses standard 50x50 map files, extracting walls, doors, and lights with 100% geometric fidelity in under 2 seconds.
3. Dynamic plugin registry hot-reloads custom tools and mounts sandboxed UI extension slots without dropping active WebSocket connections.
4. OpenAPI 3.1 documentation and FastMCP tool manifests are aggregated and accessible via interactive Swagger UI and CLI endpoints.

## Linked User Stories
- [`US-0008: MCP Tool Invocation for Autonomous AI Agents`](../../user_stories/accepted/us-0008-mcp-tool-invocation-for-agents.md)
- [`US-0033: Universal VTT Map Importer and Scriptable Grid Tiles`](../../user_stories/accepted/us-0033-universal-vtt-map-importer-and-scriptable-tiles.md)
- [`US-0035: Runtime MCP Tool Hot-Reloading and Web Component Extension Slots`](../../user_stories/accepted/us-0035-runtime-mcp-tool-hot-reloading-and-extension-slots.md)

## Implementing Backlog Tasks
- [`TASK-0041: FastMCP Gateway Server Modular Decomposition`](../../backlog/complete/0041-fastmcp-gateway-server-modular-decomposition.md)
- [`TASK-0057: Universal VTT Importer & Dynamic MCP Tool Registry`](../../backlog/complete/0057-universal-vtt-importer-and-custom-mcp-tool-registry.md)
- [`TASK-0172: Dynamic FastMCP Tool Hot-Reloading Registry`](../../backlog/proposed/0172-dynamic-fastmcp-tool-hot-reloading-registry.md)
- [`TASK-0173: Universal VTT Door and Dynamic Lighting Parser`](../../backlog/proposed/0173-universal-vtt-door-and-lighting-parser.md)
- [`TASK-0174: Community Plugin UI Extension Slots Microfrontend`](../../backlog/proposed/0174-community-plugin-ui-extension-slots-microfrontend.md)
