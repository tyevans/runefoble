"""ASGI application for the streamable HTTP MCP endpoint.

uvicorn serves this module in the gateway-mcp container (`gateway_mcp.asgi:app`).
`gateway_mcp.server.main` serves the same application when run directly.
"""

from gateway_mcp.container import GatewayMcpContainer
from gateway_mcp.server import build_http_app

app = build_http_app(GatewayMcpContainer.default())
