---
id: '0605'
title: Gateway MCP Narration and Session Resources Call The Watcher and Game Session
status: Refined
created: 2026-11-17
dependencies:
- TASK-0603
- TASK-0609
governing_adrs:
- ADR-0002
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0001
- PRD-0022
governing_stories:
- US-0007
- US-0008
target_release: 0.9.0
severity: critical
source_audits:
- w1-gateway-mcp.md
---

# TASK-0605: Gateway MCP Narration and Session Resources Call The Watcher and Game Session

## Status
Refined

## Summary
`narrate_with_the_watcher` returns a fixed template and does not call The Watcher. The `session://active` and `encounter://current` resources return fixed data for campaign `camp1`. `execute_agent_action_plan` needs the same check. Replace them with calls to `the_watcher` and `game_session` public routes.

## Problem Statement
- `gateway/mcp/src/gateway_mcp/tools/orchestration.py:12-22`: `narrate_with_the_watcher` returns a fixed template and does not call `services/the_watcher`.
- `gateway/mcp/src/gateway_mcp/resources/session.py:11-38`: `session://active` and `encounter://current` return fixed data for `camp1` and `enc-camp1`.
- Agents receive narration that does not depend on game state.

Source: `.audit/reports/w1-gateway-mcp.md` F1.

## Documentation & Architecture Review
- `docs/explanation/the-watcher-autonomous-dm.md`: The Watcher proposes narration. The gateway must forward, not invent.
- ADR-0002: orchestration is event-driven. Use the public route, not internals.
- `docs/how-to/add-a-watcher-ai-tool.md`: update the example.

## Product & User Story References
- `docs/project/user_stories/accepted/us-0007-autonomous-dm-session-execution.md`
- `docs/project/user_stories/accepted/us-0008-mcp-tool-invocation-for-agents.md`
- `docs/project/product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md`

## Detailed Specification & Implementation Plan
1. `narrate_with_the_watcher` calls The Watcher narration route. It passes the campaign and session ids from the tool input. The response is returned unchanged.
2. `session://active` and `encounter://current` read `game_session` routes for the active session. Resource URIs take the campaign id from the caller. No fixed id.
3. `execute_agent_action_plan` calls The Watcher action route (see TASK-0609 for id rules).
4. Use the shared client from TASK-0603.

## Frontdoor Blackbox Test Plan
- Before fix: `narrate_with_the_watcher` returns the same template for two different scenes (test fails).
- After fix: narration text differs when the session state differs, because it comes from The Watcher route.
- After fix: reading `session://active` after creating a session through the game session route returns that session.
- After fix: reading the resource for an unknown session returns an error, not `camp1`.

## Definition of Done
1. No fixed template and no `camp1` or `enc-camp1` literals remain in `gateway/mcp`.
2. Tools and resources call services. Files under 500 lines.
3. Blackbox tests pass. Gateway MCP suite passes.
4. Ruff check and format pass.
5. Tool and resource docs updated.
