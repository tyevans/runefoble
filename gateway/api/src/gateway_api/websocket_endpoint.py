"""Campaign WebSocket at /ws/campaigns/{campaign_id} (TASK-0883).

The gateway admits the caller with `campaign.view`. Each action frame names its session. The
gateway checks only that the session is linked to this campaign (`game_session#campaign`). It
then sends the action to the owner route in `campaign_actions`, with the caller's token. The
owner decides and publishes its own event. The gateway applies no action policy.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import WebSocket
from gateway_api.campaign_actions import ACTIONS
from gateway_api.campaign_owner_call import send_owner_call
from gateway_api.websocket_auth import admit_gateway_websocket
from gateway_api.websocket_manager import ws_campaign_manager
from runefoble_auth.errors import AuthzError
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.principal import VerifiedPrincipal
from runefoble_auth.websocket import (
    action_authorizer,
    bearer_token_from_subprotocols,
    send_socket_error,
    serve_authorized_socket,
)
from runefoble_auth.zitadel import ZitadelAuthService

logger = logging.getLogger("runefoble.gateway.websocket_endpoint")


async def _session_in_campaign(session_id: str, campaign_id: str) -> bool:
    """True when `game_session#campaign` links the session to the campaign (ADR-0015 a)."""
    links = await get_spicedb_client().read_relationships(
        resource_type="game_session", resource_id=session_id, relation="campaign"
    )
    return any(link.subject_id == campaign_id for link in links)


async def campaign_websocket_endpoint(
    websocket: WebSocket,
    campaign_id: str,
    auth_service: ZitadelAuthService | None = None,
) -> None:
    """Handle the campaign socket at /ws/campaigns/{campaign_id}."""
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
        action = data.get("action") or data.get("type") or "unknown"
        build = ACTIONS.get(action)
        if build is None:
            await send_socket_error(
                websocket,
                "UNKNOWN_ACTION",
                f"Unknown action '{action}' has no owner route",
                action=action,
            )
            return

        session_id = data.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            await send_socket_error(
                websocket, "INVALID_FRAME", f"Action '{action}' needs a session_id", action=action
            )
            return

        try:
            linked = await _session_in_campaign(session_id, campaign_id)
        except AuthzError:
            logger.error("Campaign socket cannot read session links for '%s'", session_id)
            await send_socket_error(
                websocket,
                "AUTHORIZATION_UNAVAILABLE",
                "SpiceDB could not check the session link",
                action=action,
            )
            return
        if not linked:
            logger.warning("Campaign socket refused session '%s' for campaign", session_id)
            msg = f"Session '{session_id}' is not linked to campaign '{campaign_id}'"
            await send_socket_error(websocket, "PERMISSION_DENIED", msg, action=action)
            return

        try:
            call = build(session_id, data)
        except ValueError as exc:
            await send_socket_error(websocket, "INVALID_FRAME", str(exc), action=action)
            return

        token = bearer_token_from_subprotocols(list(websocket.scope.get("subprotocols", [])))
        if token is None:
            raise RuntimeError("An admitted campaign socket has no bearer subprotocol")
        if not await send_owner_call(websocket, action, call, token):
            return

        subject_id = principal.user_id
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
            ws,
            action_authorizer("campaign.view", campaign_id),
            verifier=auth_service,
            denial_message=denied_msg,
        ),
        on_open=open_room,
        on_frame=handle_frame,
        on_close=lambda: ws_campaign_manager.disconnect(campaign_id, websocket),
    )


__all__ = ["campaign_websocket_endpoint"]
