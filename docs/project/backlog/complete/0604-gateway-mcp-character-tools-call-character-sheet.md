---
id: '0604'
title: Gateway MCP Character Tools Call Character Sheet Service Frontdoors
status: Complete
created: 2026-11-17
dependencies:
- TASK-0603
governing_adrs:
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0006
- PRD-0022
governing_stories:
- US-0008
- US-0015
target_release: 0.9.0
severity: critical
source_audits:
- w1-gateway-mcp.md
---

# TASK-0604: Gateway MCP Character Tools Call Character Sheet Service Frontdoors

## Status
Complete

## Summary
The MCP character tools return echoes and hardcoded characters. `get_character_sheet` returns "Valeros" or "Kyra" by id. `modify_character_hp` uses a fixed baseline. Replace these with calls to the `character_sheet` service through its public routes.

## Problem Statement
- `gateway/mcp/src/gateway_mcp/tools/character.py:11-29`: `inspect_inventory` returns fixed items.
- `character.py:32-51`: `get_character_sheet` hardcodes "Valeros" and "Kyra" by id.
- `character.py:105-135`: `modify_character_hp` uses baseline 30 or 45 and ignores the character.
- `character.py:54-64`, `67-102`, `138-158`: `apply_absentee_penalty`, `cast_spell`, and condition tools return echoes. Nothing is persisted.

Source: `.audit/reports/w1-gateway-mcp.md` F1.

## Documentation & Architecture Review
- Same client module as TASK-0603 (`gateway_mcp/clients/services.py`). Add a `CHARACTER_SHEET_URL` setting.
- `docs/reference/fastmcp-gateway.md` tool inventory.
- ADR-0007: character state lives in `character_sheet`.

## Product & User Story References
- `docs/project/product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md`
- `docs/project/user_stories/accepted/us-0015-character-inventory-equipment-tracking.md`
- `docs/project/user_stories/accepted/us-0008-mcp-tool-invocation-for-agents.md`

## Detailed Specification & Implementation Plan
1. Rewrite the seven character tools to call `character_sheet` public routes (read sheet, inventory, HP change, condition, spell slot, absentee penalty).
2. Remove hardcoded names, the 30/45 baseline, and echo returns.
3. Map a missing character to a tool error from the upstream 404.
4. Add tests that show a change made through MCP is visible through the character sheet route.

## Frontdoor Blackbox Test Plan
- Before fix: `modify_character_hp` with -5 through MCP, then `get_character_sheet` through the sheet route shows no change (test fails).
- After fix: HP in the sheet route equals the value set through MCP.
- After fix: `get_character_sheet` for an unknown id returns a tool error, not "Valeros".
- After fix: `apply_condition` through MCP is visible in the sheet route.

## Definition of Done
1. No hardcoded character names or baselines remain in `gateway/mcp`.
2. Tools call the service. Files under 500 lines.
3. Blackbox tests pass. Gateway MCP and character sheet suites pass.
4. Ruff check and format pass.
5. Tool inventory docs corrected.
