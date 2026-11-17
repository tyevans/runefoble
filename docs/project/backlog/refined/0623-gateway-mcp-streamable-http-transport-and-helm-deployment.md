---
id: '0623'
title: Gateway MCP Streamable HTTP Transport and Helm Deployment
status: Refined
created: 2026-11-17
dependencies:
- TASK-0620
- TASK-0489
governing_adrs:
- ADR-0001
- ADR-0005
governing_prds:
- PRD-0022
governing_stories:
- US-0008
target_release: 0.9.0
severity: medium
source_audits:
- w1-gateway-mcp.md
- w1-gates-infra.md
---

# TASK-0623: Gateway MCP Streamable HTTP Transport and Helm Deployment

## Status
Refined

## Summary
`gateway/mcp` runs only as a stdio process (`server.py:89-91`, `mcp.run()` with the default transport). No Helm Deployment, Service, image, or Swagger/MCP route exists, and `docs/reference/ports-and-endpoints.md:299` claims the service serves MCP. Serve the MCP protocol over streamable HTTP, build its image, and deploy it through Helm. Dynamic tool registry sharing across processes is out of scope (see TASK-0489 and the `w1-gateway-mcp` F3 follow-up).

## Problem Statement
- `gateway/mcp/src/gateway_mcp/server.py:89-91` runs stdio only. No `deployments/helm` template mentions mcp (`grep -i mcp deployments/helm` is empty).
- `docs/reference/ports-and-endpoints.md:299` lists gateway-mcp as a served protocol endpoint. That is false today.
- Root `gateway/mcp/main.py` prints a placeholder (dead, removed by TASK-0489 family work).

## Documentation & Architecture Review
- `docs/reference/fastmcp-gateway.md` describes transports; update it to the chosen transport.
- `docs/reference/ports-and-endpoints.md` line ~299: correct it in this task.
- ADR-0001: any tool that mutates state must check SpiceDB; deployment does not change this, but the Helm deployment must not expose anonymous mutation. Anonymous tool execution is covered by the gateway/mcp audit findings F2 and F5, which are tracked separately; this task must not expose the endpoint on the public ingress.
- ADR-0005: Deployment and Service follow the `services.yaml` pattern.

## Product & User Story References
- PRD-0022 (modder platform and MCP registry), US-0008 (MCP tool invocation for agents), in `docs/project/product/accepted/` and `docs/project/user_stories/accepted/`.

## Detailed Specification & Implementation Plan
1. Change `server.py` `main()` to run `mcp.run(transport="streamable-http")` with host and port from `GATEWAY_MCP_HOST` (default `0.0.0.0`) and `GATEWAY_MCP_PORT` (default `8012`). Verify the FastMCP version API before coding (use context7 `fastmcp` or the installed package).
2. Add `services.gatewayMcp` to `values.yaml` (image `runefoble/gateway-mcp:0.1.0`, port 8012) and a Deployment and ClusterIP Service in a new template `gateway-mcp.yaml`. Do not add an ingress path.
3. Add `http://gateway-mcp:8012/openapi.json` only if the transport exposes OpenAPI. Otherwise document the exemption from Hard Invariant 5 in `docs/reference/ports-and-endpoints.md`.
4. Add the image to `make images` (TASK-0620) with `APP=gateway_mcp.server:mcp`-style entry or a `main` function; choose the form that matches the server module.
5. Correct `ports-and-endpoints.md` line ~299 and `fastmcp-gateway.md` transport text.
6. Delete nothing else here; root stub removal belongs to TASK-0489.

## Frontdoor Blackbox Test Plan
- Before fix: a client connecting to `http://gateway-mcp:8012/mcp` finds no server; `helm template` has no `gateway-mcp` Service.
- After fix: an MCP client using the public streamable-HTTP protocol (`mcp` Python client) initializes a session against the running container and lists tools; the list contains the 16 static tools documented in `fastmcp-gateway.md`. The test lives in `tests/test_blackbox_gateway_mcp_http.py`.
- `helm template` renders a `gateway-mcp` Service on 8012 with no ingress rule.

## Definition of Done
1. `server.py` serves streamable HTTP; stdio mode remains available behind an explicit flag only if a developer tool needs it.
2. Helm Deployment and Service render and lint.
3. Image builds through `make images`.
4. Reference docs corrected.
5. MCP client blackbox test passes.
6. No file above 500 lines.

## Orchestrator Addenda (2026-11-17, round 2)

Source: `.audit/synth/discovered-round2.md`.

- gateway/mcp/src/gateway_mcp/settings.py defaults point at localhost. The gatewayMcp URL keys in values.yaml are not rendered into any template. Render them into the gateway MCP Deployment and remove the localhost defaults for deployed use.
