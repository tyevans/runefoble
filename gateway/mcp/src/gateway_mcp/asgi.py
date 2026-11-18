"""ASGI application for the streamable HTTP MCP endpoint.

uvicorn serves this module in the gateway-mcp container (`gateway_mcp.asgi:app`).
`gateway_mcp.server.main` serves the same application when run directly.
"""

from gateway_mcp.server import configure_dynamic_event_bus, mcp
from runefoble_platform.config import PlatformSettings

configure_dynamic_event_bus(PlatformSettings())
app = mcp.streamable_http_app()
