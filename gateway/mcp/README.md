# gateway-mcp

The Runefoble Model Context Protocol (MCP) gateway. It serves tabletop tools, resources and prompts to LLM agents over streamable HTTP at `/mcp`.

- Run: `uv run python -m gateway_mcp.server`. Set the upstream service URLs first.
- ASGI app: `gateway_mcp.asgi:app`.
- Reference: [`docs/reference/fastmcp-gateway.md`](../../docs/reference/fastmcp-gateway.md).
- Add a tool: [`docs/how-to/add-a-watcher-ai-tool.md`](../../docs/how-to/add-a-watcher-ai-tool.md).
