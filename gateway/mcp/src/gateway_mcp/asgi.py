"""ASGI application for the streamable HTTP MCP endpoint.

uvicorn serves this module in the gateway-mcp container (`gateway_mcp.asgi:app`).
`gateway_mcp.server.main` serves the same application when run directly.
"""

from gateway_mcp.server import build_http_app, configure_dynamic_event_bus
from runefoble_platform.config import PlatformSettings

configure_dynamic_event_bus(PlatformSettings())
app = build_http_app()
