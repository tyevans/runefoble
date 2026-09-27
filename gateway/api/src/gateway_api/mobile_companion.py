"""Spatial Companion Mobile WebRTC Audio & Haptic Ping Gateway Facade.

Governing ADRs: ADR-0002, ADR-0005, ADR-0013.
Re-exports:
- MobileCompanionManager, mobile_companion_manager from gateway_api.companion.manager
- mobile_companion_websocket_endpoint from gateway_api.companion.endpoint
- router from gateway_api.companion.router
"""

from __future__ import annotations

from gateway_api.companion import (
    MobileCompanionManager,
    mobile_companion_manager,
    mobile_companion_websocket_endpoint,
    publish_companion_event,
)
from gateway_api.companion import (
    companion_router as router,
)

__all__ = [
    "MobileCompanionManager",
    "mobile_companion_manager",
    "mobile_companion_websocket_endpoint",
    "publish_companion_event",
    "router",
]
