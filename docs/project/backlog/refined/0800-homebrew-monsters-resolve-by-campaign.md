---
id: '0800'
title: Homebrew Monsters Resolve by Campaign in the Compendium Lookup
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0001
governing_prds: []
governing_stories: []
target_bc: rules_compendium
target_release: 0.9.0
---

# TASK-0800: Homebrew Monsters Resolve by Campaign in the Compendium Lookup

## Status
Refined. Found during batch 23 integration, 2026-11-17.

## Summary
The compendium monster lookup ignores the campaign, so a homebrew monster cannot be found and its challenge rating cannot be read by the MCP encounter tool.

## Problem Statement
- `services/rules_compendium/src/rules_compendium/routers/rules.py:76`: `get_monster` takes no `campaign_id`.
- `gateway/mcp/src/gateway_mcp/owning_services.py:308`: does not pass the campaign.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0001.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add an optional `campaign_id` query to the monster lookup. With it, homebrew monsters of that campaign resolve, after a `campaign.view` check.
2. The MCP encounter tool passes the campaign.

## Frontdoor Blackbox Test Plan
- A homebrew monster created through the public route resolves with its campaign id and its CR reaches the MCP encounter.
- A stranger without `campaign.view` gets 403.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `.audit/work/0792.md` (Discovered)
