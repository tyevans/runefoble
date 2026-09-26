---
id: 0035
title: Runtime MCP Tool Hot-Reloading and Web Component Extension Slots
status: Accepted
created: 2026-09-25
governing_prd: PRD-0001
---

# US-0035 — Runtime MCP Tool Hot-Reloading and Web Component Extension Slots

## Governing PRD
- [`PRD-0001: The Watcher AI Dungeon Master and Real-Time Board Animator`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)

## User Story

**As a** plugin developer extending Runefoble’s core capabilities (Alex),  
**I want to** hot-reload custom FastMCP tools and mount custom Lit Web Component plugins into dedicated UI slots,  
**So that** I can build and iterate on community extensions without recompiling the platform core.

## Acceptance Criteria

1. **Dynamic MCP Tool Registry**: FastMCP server supports registering and unregistering tools at runtime via a secure administrative API.
2. **Web Component Extension Slots**: The frontend design system exposes `<slot name="hud-widget">` and `<slot name="dice-panel">` extension points.
3. **Sandboxed Plugin Execution**: Third-party plugins execute within isolated Shadow DOM boundaries with scoped SpiceDB Zanzibar API tokens.
