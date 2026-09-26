---
id: 0057
title: Universal VTT Importer and Dynamic MCP Tool Registry
status: Proposed
created: 2026-09-25
dependencies: [TASK-0005, TASK-0007, TASK-0020]
governing_adrs: [ADR-0007, ADR-0008]
target_release: 0.2.1
---

# TASK-0057: Universal VTT Importer and Dynamic MCP Tool Registry

## Status
Proposed

## Summary
Add Universal VTT (`.dd2vtt`) map importing in `services/board_state` and dynamic runtime FastMCP tool registration in `gateway/mcp` for developers and modders (Alex).

## Problem Statement
Modders and developers cannot easily import community battlemap standards or dynamically register new FastMCP tools without restarting the gateway infrastructure.

## Scope of Work
1. **Universal VTT Parser**: Implement parser in `board_state` converting `.dd2vtt` JSON structures (walls, portals, lights, resolution) into `BoardStateAggregate` wall segments and grid dimensions.
2. **Dynamic FastMCP Tool Registry**: Provide an administrative API to register, update, and deregister FastMCP tools at runtime with validation.
3. **Web Component Slot Extension Guide**: Document and test Storybook extension slots (`<slot name="hud-widget">`).

## Acceptance Criteria
1. Successfully imports sample `.dd2vtt` file and reproduces wall obstruction lines in `board_state`.
2. New MCP tools register dynamically and appear in `/mcp/tools` without gateway downtime.
3. Automated test suite for map import and tool registration.
