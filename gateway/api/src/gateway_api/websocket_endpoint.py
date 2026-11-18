"""Real-time WebSocket routing endpoint handler for campaign streams."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket
from gateway_api.dependencies import get_event_bus
from gateway_api.websocket_auth import admit_gateway_websocket
from gateway_api.websocket_manager import ws_campaign_manager
from gateway_api.websocket_validator import (
    KNOWN_ACTIONS,
    MOVE_ACTIONS,
    WebSocketActionValidator,
    default_action_validator,
)
from runefoble_auth.principal import VerifiedPrincipal
from runefoble_auth.websocket import send_socket_error, serve_authorized_socket
from runefoble_auth.zitadel import ZitadelAuthService
from runefoble_platform.event_publish import publish_best_effort

logger = logging.getLogger("runefoble.gateway.websocket_endpoint")
SESSION_ACTIONS = ("modify_hp", "apply_condition", "clear_condition")


def _resolve_stream(action: str) -> str:
    if action in MOVE_ACTIONS:
        return "runefoble.events.board"
    if action in SESSION_ACTIONS:
        return "runefoble.events.session"
    return "runefoble.events.watcher"


async def _publish_event(
    action: str, campaign_id: str, subject_id: str, data: dict[str, Any]
) -> None:
    if bus := get_event_bus():
        payload = {
            "event_type": f"runefoble.events.{action}",
            "campaign_id": campaign_id,
            "user_id": subject_id,
            "action": action,
            "data": data,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        await publish_best_effort(bus, _resolve_stream(action), payload)


async def campaign_websocket_endpoint(
    websocket: WebSocket,
    campaign_id: str,
    validator: WebSocketActionValidator | None = None,
    auth_service: ZitadelAuthService | None = None,
) -> None:
    """Handle Zanzibar-protected WebSocket connections at /ws/campaigns/{campaign_id}."""
    action_validator = validator or default_action_validator

    async def may_connect(subject_id: str) -> bool:
        return await action_validator.validate_connect(campaign_id, subject_id)

    # 1. On connect: verify viewer/subject has campaign:view or campaign:read permission
    denied_msg = (
        f"Zanzibar authorization denied: insufficient permissions to view campaign '{campaign_id}'"
    )

    async def open_room(principal: VerifiedPrincipal) -> bool:
        ws_campaign_manager.register(campaign_id, websocket)
        await websocket.send_json(
            {
                "type": "connected",
                "campaign_id": campaign_id,
                "user_id": principal.user_id,
                "message": "Connected to Runefoble real-time campaign stream. The Watcher is listening.",
            }
        )
        return True

    async def handle_frame(principal: VerifiedPrincipal, data: dict[str, Any]) -> None:
        subject_id = principal.user_id
        action = data.get("action") or data.get("type") or "unknown"

        if action not in KNOWN_ACTIONS:
            await send_socket_error(
                websocket, "UNKNOWN_ACTION", f"Unknown action '{action}'", action=action
            )
            return

        # 2. Verify permission for incoming action
        if not await action_validator.validate_action(campaign_id, subject_id, action, data):
            logger.warning(
                "Zanzibar denied action '%s' for subject '%s' in campaign '%s'",
                action,
                subject_id,
                campaign_id,
            )
            msg = f"Zanzibar authorization denied: insufficient permissions for action '{action}'"
            await send_socket_error(websocket, "PERMISSION_DENIED", msg, action=action)
            return

        # 3. Publish authorized event to Redis stream
        await _publish_event(action, campaign_id, subject_id, data)

        # 4. Broadcast state to connected party clients
        broadcast = {
            "type": data.get("type", action),
            "action": action,
            "status": "applied",
            "campaign_id": campaign_id,
            "user_id": subject_id,
            **{k: v for k, v in data.items() if k not in ("type", "action")},
        }
        await ws_campaign_manager.broadcast(campaign_id, broadcast)

    await serve_authorized_socket(
        websocket,
        admit=lambda ws: admit_gateway_websocket(
            ws, may_connect, verifier=auth_service, denial_message=denied_msg
        ),
        on_open=open_room,
        on_frame=handle_frame,
        on_close=lambda: ws_campaign_manager.disconnect(campaign_id, websocket),
    )


__all__ = [
    "campaign_websocket_endpoint",
    "logger",
]
