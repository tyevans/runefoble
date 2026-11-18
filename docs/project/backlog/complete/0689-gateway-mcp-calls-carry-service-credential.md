---
id: '0689'
title: Gateway MCP Service Calls Carry a Kubernetes Secret Service Credential
status: Complete
created: 2026-11-17
dependencies:
- TASK-0529
- TASK-0626
- TASK-0623
governing_adrs:
- ADR-0015
governing_prds: []
governing_stories: []
target_release: 0.9.0
---

# TASK-0689: Gateway MCP Service Calls Carry a Kubernetes Secret Service Credential

## Status
Complete

## Summary
`gateway_mcp` calls board_state, character_sheet, game_session and rules_compendium over HTTP. It sends no credential, and the receiving services accept any caller on the cluster network. This task adds a service credential, read from a Kubernetes Secret, to the shared service client. The receiving routes reject calls without it.

## Problem Statement
- `libs/runefoble_platform/src/runefoble_platform/service_client/client.py` and `gateway/mcp/src/gateway_mcp/clients/services.py` build requests with no credential.
- The MCP tools run with no user principal. Routes that trust only the network path accept them.
- Report 0622: the inference worker has the same gap. TASK-0529 covers it. This task covers the MCP caller and the receivers it uses.

## Documentation & Architecture Review
- ADR-0015 (e): the calling service presents a credential from a Kubernetes Secret mounted in its pod. The receiver rejects calls that do not present it.
- ADR-0015 (c): user identity still comes from the verified Zitadel token (TASK-0532). The service credential does not replace it.
- `docs/reference/platform-services.md`: document the new Secret key.

## Product & User Story References
None. Platform security control with no user-facing change.

## Detailed Specification & Implementation Plan
1. Add a credential setting to the shared service client (`RUNEFOBLE_SERVICE_CREDENTIAL`, read from a Secret). The client sends it in a dedicated header, for example `X-Runefoble-Service-Credential`. Do not use `Authorization`, because that carries the user token. Align the header name with TASK-0529 before coding.
2. Receivers used by gateway_mcp (board_state, character_sheet, game_session, rules_compendium) accept the header only on the routes gateway_mcp calls. Compare with `hmac.compare_digest`. Refuse to start when the credential is unset outside tests.
3. Helm: a Secret reference in the gateway MCP Deployment (from TASK-0623) and the four receivers.
4. The gateway API keeps verifying user tokens. It does not get the MCP credential.

## Frontdoor Blackbox Test Plan
- An MCP tool call through the MCP server with the credential returns data from the receiving service.
- The same request sent directly to a receiver without the header returns 401 or 403.
- A receiver started without the credential refuses to start.

## Definition of Done
- All gateway_mcp service calls carry the credential. Receivers reject calls without it.
- `uv run pytest` and `make lint` pass. `make helm-template` renders the Secret references.
- Docs updated.

## Audit Provenance

- Severity: high
- Source audits: `work/0604.md`, `work/0622.md`, `work/0603.md`
