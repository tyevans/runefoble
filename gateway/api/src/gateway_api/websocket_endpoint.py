"""Real-time WebSocket routing endpoint handler for campaign streams."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from gateway_api.websocket_auth import admit_gateway_websocket
from gateway_api.websocket_manager import ws_campaign_manager
from gateway_api.websocket_validator import (
    MOVE_ACTIONS,
    WebSocketActionValidator,
    default_action_validator,
)
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
    import gateway_api.main as gw_main

    if bus := gw_main.get_event_bus():
        payload = {
            "event_type": f"runefoble.events.{action}",
            "campaign_id": campaign_id,
            "user_id": subject_id,
            "action": action,
            "data": data,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        await publish_best_effort(bus, _resolve_stream(action), payload)


async def _send_denied(websocket: WebSocket, action: str, msg: str) -> None:
    await websocket.send_json(
        {"type": "error", "code": "PERMISSION_DENIED", "message": msg, "action": action}
    )


async def campaign_websocket_endpoint(
    websocket: WebSocket,
    campaign_id: str,
    validator: WebSocketActionValidator | None = None,
    auth_service: ZitadelAuthService | None = None,
) -> None:
    """Handle Zanzibar-protected WebSocket connections at /ws/campaigns/{campaign_id}."""
    action_validator = validator or default_action_validator
    principal = await admit_gateway_websocket(websocket, auth_service)
    if principal is None:
        return
    subject_id = principal.user_id

    # 1. On connect: verify viewer/subject has campaign:view or campaign:read permission
    if not await action_validator.validate_connect(campaign_id, subject_id):
        logger.warning(
            "WebSocket connect rejected: subject '%s' lacks view on campaign '%s'",
            subject_id,
            campaign_id,
        )
        denied_msg = f"Zanzibar authorization denied: insufficient permissions to view campaign '{campaign_id}'"
        await _send_denied(websocket, "connect", denied_msg)
        await websocket.close(code=4003, reason="Forbidden: insufficient permissions for campaign")
        return

    await ws_campaign_manager.connect(campaign_id, websocket, subject_id)

    try:
        await websocket.send_json(
            {
                "type": "connected",
                "campaign_id": campaign_id,
                "user_id": subject_id,
                "message": "Connected to Runefoble real-time campaign stream. The Watcher is listening.",
            }
        )

        while True:
            data = await websocket.receive_json()
            action = data.get("action") or data.get("type") or "unknown"

            # 2. Verify permission for incoming action
            if not await action_validator.validate_action(campaign_id, subject_id, action, data):
                logger.warning(
                    "Zanzibar denied action '%s' for subject '%s' in campaign '%s'",
                    action,
                    subject_id,
                    campaign_id,
                )
                msg = (
                    f"Zanzibar authorization denied: insufficient permissions for action '{action}'"
                )
                await _send_denied(websocket, action, msg)
                continue

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
            await ws_campaign_manager.broadcast_to_campaign(campaign_id, broadcast)

    except WebSocketDisconnect:
        ws_campaign_manager.disconnect(campaign_id, websocket)


__all__ = [
    "campaign_websocket_endpoint",
    "logger",
]
