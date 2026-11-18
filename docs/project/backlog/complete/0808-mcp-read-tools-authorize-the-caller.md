---
id: '0808'
title: "MCP Read Tools Authorize the Caller Before They Read Owner Data"
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: gateway_mcp
target_release: 0.9.0
---

# TASK-0808: MCP Read Tools Authorize the Caller Before They Read Owner Data

## Status
Complete

## Summary
The MCP tools `get_character_sheet` and `inspect_inventory` read any character by id. They call character_sheet with only the service credential, and character_sheet skips the object check for that credential.

## Problem Statement
- `gateway/mcp/src/gateway_mcp/tools/character.py:20-40`: both tools call `OwningServices().get_character(...)` with no caller identity and never call `authorize_tool_call`.
- `services/character_sheet/src/character_sheet/dependencies.py:111-121` (`_check_caller`): with only the service credential, no object check runs.
- Other MCP tools may follow the same pattern.

## Documentation & Architecture Review
- AGENTS.md Hard Invariant 1 (SpiceDB) and DoR 9.
- ADR-0001, ADR-0015. `docs/how-to/verify-identity-in-fastapi-and-websockets.md`, `docs/how-to/define-spicedb-zanzibar-permissions.md`.

## Product & User Story References
None. Security defect.

## Detailed Specification & Implementation Plan
1. List every MCP tool that reads or changes owner data. For each, check the caller through `authorize_tool_call` (or forward the caller bearer to the owner) before the owner call.
2. Decide whether character_sheet should accept the service credential for reads at all. If a caller identity is always available, remove `allow_service` from the view routes.
3. Record the tool-to-permission table in `docs/reference/fastmcp-gateway.md`.

## Frontdoor Blackbox Test Plan
- An MCP caller without `character.view` on a character gets an error from `get_character_sheet` and `inspect_inventory`, and no sheet data.
- The owner of the character gets the sheet.
- The same two checks for every other tool in the table.

## Definition of Done
- The test plan passes, including with a live SpiceDB (`make test-authz-live`).
- `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high (authorization)
- Source audits: `.audit/research/gateways.md` (urgent items, verified by the orchestrator 2026-11-18)
