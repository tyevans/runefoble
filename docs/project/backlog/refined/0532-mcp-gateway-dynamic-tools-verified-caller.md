---
id: '0532'
title: MCP Gateway Dynamic Tools Take Caller Identity from the Verified Principal
status: Refined
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0521
- TASK-0623
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0007
governing_prds:
- PRD-0022
governing_stories:
- US-0013
target_release: 0.9.0
severity: critical
source_audits:
- w1-gateway-mcp.md
- w3-authz-coverage.md
---

# TASK-0532: MCP Gateway Dynamic Tools Take Caller Identity from the Verified Principal

## Status
Refined

## Summary
The MCP gateway's dynamic tool routes take the author and caller from the request body and an optional header. Anonymous calls pass. Make every tool route and every tool call use the verified principal. Record the author from the token, never from the body.

## Problem Statement
- `gateway/mcp/src/gateway_mcp/dynamic/auth.py:63-64` (`enforce_tool_auth`) returns without a check when `user_id` is falsy. Audit w1-gateway-mcp F2.
- `gateway/mcp/src/gateway_mcp/routers/tools_registry.py:40-49` sets `author_id = payload.author_id or x_user_id`. The body wins and the author receives the SpiceDB `author` relation.
- `tools_registry.py:87-93` (delete) and `:103-104` (execute) use the same optional identity. Anonymous callers delete other authors' tools and execute handlers. Audit w3-authz F8 (identity part).
- `gateway/mcp/src/gateway_mcp/tools/orchestration.py:25-130` runs `execute_agent_action_plan`, which calls any registered tool with no caller identity. Audit w1-gateway-mcp F5 (identity part only; the static-tool permission checks belong to the authorization theme).
- `gateway/api/src/gateway_api/main.py:88-89` mounts this router with no auth dependency.

## Documentation & Architecture Review
- Permission names on register and execute (`mcp_tool` manage and execute) belong to the authorization theme. This task changes identity only.
- Sandboxed `exec` in `gateway/mcp/src/gateway_mcp/sandbox.py:155` is an authorization and security defect outside this task. Note it in the PR and in the index.
- The MCP protocol transport must carry the token. TASK-0623 (streamable HTTP) has no auth rule yet. Add the bearer rule to TASK-0623 before this task starts. See the index report.

## Product & User Story References
- PRD-0022 (modder platform and MCP registry). US-0013.

## Detailed Specification & Implementation Plan
1. REST routes under `/mcp/tools` depend on `require_principal` (TASK-0520). Mount them behind that dependency in `main.py` (gateway).
2. `tools_registry.py`: delete `author_id` and `user_id` from request payloads for register, update, and execute. The author is `principal.user_id`. Store it on the tool record.
3. `dynamic/auth.py`: delete the `if not user_id: return` branch. The function takes a non-null principal id.
4. Tool execution: pass the verified caller id into the tool context. `orchestration.py` takes the caller from the request context and passes it to each tool call. Static tools that need a caller get it through the same context.
5. MCP protocol calls: the server reads the caller from the transport bearer token defined in TASK-0623 (after its amendment). A call without a valid token is refused before tool dispatch.
6. Delete every `X-User-Id` and `x-user-id` read in `gateway/mcp/src`.

## Frontdoor Blackbox Test Plan
HTTP tests against the MCP gateway app, plus the MCP client once TASK-0623 lands.
- Before: anonymous `POST /mcp/tools/register` returns 200 with a body `author_id`. Anonymous `DELETE /mcp/tools/{name}` returns 200.
- After:
  - Register, update, delete, and execute return 401 with no bearer.
  - A body `author_id` that differs from the token subject is ignored. The stored author equals the token subject.
  - An MCP client call with no token is refused before dispatch.

## Definition of Done
1. `grep -rn "author_id\|x_user_id\|x-user-id" gateway/mcp/src` returns no identity-from-input use.
2. MCP gateway test suite passes with the signing issuer.
3. The MCP how-to (`docs/how-to/add-a-watcher-ai-tool.md` and the dynamic tools how-to) shows the bearer requirement.
4. `docs/reference/fastmcp-gateway.md` documents the caller rule.
5. No file exceeds 500 lines.
