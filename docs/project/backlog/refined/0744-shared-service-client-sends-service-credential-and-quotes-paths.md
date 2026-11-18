---
id: '0744'
title: Shared Service Client Sends the Service Credential and Quotes Path Segments
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0022
governing_stories:
- US-0008
target_bc: core
target_release: 0.9.0
---
# TASK-0744: Shared Service Client Sends the Service Credential and Quotes Path Segments

## Status
Refined. Found by the refactor audit round refactor-r1 and checked against the code on 2026-11-17.

## Summary
The shared service client sends only `Authorization` and `traceparent`. It does not send the service credential (ADR-0015 e), so gateway proxies on the shared client are not identified as services. It also gives callers no helper for safe path segments. This task prepares the MCP migration.

## Problem Statement
- `libs/runefoble_platform/src/runefoble_platform/service_client/headers.py:23` (`build_upstream_headers`) adds `Authorization` and `traceparent` only.
- TASK-0689 (complete) added `X-Runefoble-Service-Credential` to the MCP-local client `gateway/mcp/src/gateway_mcp/clients/services.py`, not to the shared client.
- MCP path segments built from agent input are unquoted at `services.py:127`, `:160`, `:249`, `:275`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- `docs/reference/service-client.md`: update the header list. ADR-0015 (e).

## Product & User Story References
- PRD-0022
- US-0008

## Detailed Specification & Implementation Plan
1. Add the service credential to the shared client (constructor argument fed from settings), sent on every upstream call.
2. Add a `path(*segments)` helper in the shared client package that quotes each segment with `urllib.parse.quote(safe="")` and rejects empty segments.
3. Update `gateway/api` call sites only where the constructor changes. Do not touch MCP code here (TASK-0745).

## Frontdoor Blackbox Test Plan
- Gateway proxy test with a loopback upstream: assert the upstream receives the service credential and `traceparent`.
- Unit test: a segment with `/` or `?` is quoted.

## Definition of Done
- `docs/reference/service-client.md` lists the credential header and the path helper.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: high
- Source audits: `gateway-mcp.md (F2 part 1, section 5)`
