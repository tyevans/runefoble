"""Real-time WebSocket Zanzibar Permission Enforcement and Campaign Hub.

Facade module retaining backward compatibility for imports from gateway_api.websocket.
Re-exports:
- WebSocketActionValidator, default_action_validator from gateway_api.websocket_validator
- CampaignConnectionManager, CampaignWebSocketManager, ws_campaign_manager from gateway_api.websocket_manager
- campaign_websocket_endpoint from gateway_api.websocket_endpoint
- authenticate_websocket, extract_token_from_websocket, extract_subject_id from gateway_api.websocket_auth
"""

from __future__ import annotations

import logging

from gateway_api.websocket_auth import (
    authenticate_websocket,
    extract_subject_id,
    extract_token_from_websocket,
)
from gateway_api.websocket_endpoint import campaign_websocket_endpoint
from gateway_api.websocket_manager import (
    CampaignConnectionManager,
    CampaignWebSocketManager,
    ws_campaign_manager,
)
from gateway_api.websocket_validator import (
    DM_ACTIONS,
    HEALTH_ACTIONS,
    MOVE_ACTIONS,
    WebSocketActionValidator,
    default_action_validator,
)

logger = logging.getLogger("runefoble.gateway.websocket")

__all__ = [
    "CampaignConnectionManager",
    "CampaignWebSocketManager",
    "DM_ACTIONS",
    "HEALTH_ACTIONS",
    "MOVE_ACTIONS",
    "WebSocketActionValidator",
    "authenticate_websocket",
    "campaign_websocket_endpoint",
    "default_action_validator",
    "extract_subject_id",
    "extract_token_from_websocket",
    "logger",
    "ws_campaign_manager",
]
