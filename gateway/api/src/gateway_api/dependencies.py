"""Shared dependencies, configuration, and state for Gateway API."""

from __future__ import annotations

import logging

from gateway_api.upstreams import UpstreamRegistry
from runefoble_auth.settings import load_spicedb_settings
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.ws_groups import WebSocketGroups
from starlette.requests import HTTPConnection

logger = logging.getLogger("runefoble.gateway.dependencies")

platform_settings = PlatformSettings()
# This service checks SpiceDB permissions. Fail fast at start-up without the key (TASK-0720).
load_spicedb_settings()


event_bus_provider = EventBusProvider(platform_settings)
get_event_bus = event_bus_provider.get
set_event_bus = event_bus_provider.set


# Live session sockets, one group per session. A broadcast reaches only that session's sockets.
ws_manager = WebSocketGroups[str]()


def get_upstreams(connection: HTTPConnection) -> UpstreamRegistry:
    """FastAPI dependency: the service clients built in the gateway lifespan. Works for HTTP and WebSocket."""
    return connection.app.state.upstreams
