"""Real-time WebSocket Zanzibar Permission Enforcement and Campaign Hub.

Enforces fine-grained SpiceDB Zanzibar authorization checks on active
WebSocket connections and incoming mutative actions (ADR-0001, Hard Invariant 1).
"""

import contextlib
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from gateway_api.auth import get_spicedb_client, get_zitadel_auth_service
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_auth.zitadel import ZitadelAuthService

logger = logging.getLogger("runefoble.gateway.websocket")


class WebSocketActionValidator:
    """Validates real-time WebSocket actions against SpiceDB Zanzibar schema."""

    def __init__(self, spicedb_client: SpiceDBClient | None = None):
        self._spicedb = spicedb_client

    @property
    def spicedb(self) -> SpiceDBClient:
        return self._spicedb or get_spicedb_client()

    async def validate_connect(self, campaign_id: str, subject_id: str) -> bool:
        """Verify viewer/subject has campaign:view or campaign:read permission in SpiceDB."""
        if await self.spicedb.check_permission("campaign", campaign_id, "view", "user", subject_id):
            return True
        return await self.spicedb.check_permission(
            "campaign", campaign_id, "read", "user", subject_id
        )

    async def is_dungeon_master(self, campaign_id: str, subject_id: str) -> bool:
        """Check if subject holds DM or campaign management permissions."""
        if await self.spicedb.check_permission(
            "campaign", campaign_id, "dungeon_master", "user", subject_id
        ):
            return True
        if await self.spicedb.check_permission(
            "campaign", campaign_id, "run_session", "user", subject_id
        ):
            return True
        return await self.spicedb.check_permission(
            "campaign", campaign_id, "owner", "user", subject_id
        )

    async def validate_action(
        self,
        campaign_id: str,
        subject_id: str,
        action: str,
        data: dict[str, Any],
    ) -> bool:
        """Validate whether subject is authorized to perform action within campaign."""
        # 1. Dungeon Master and Owner bypass all gameplay mutator restrictions
        if await self.is_dungeon_master(campaign_id, subject_id):
            return True

        # 2. Token movement authorization
        if action in (
            "move_token",
            "board_move",
            "ghost_preview",
            "preview_intent",
            "confirm_intent",
            "cancel_preview",
        ):
            # Check campaign-level token movement rights
            if await self.spicedb.check_permission(
                "campaign", campaign_id, "move_token", "user", subject_id
            ):
                return True
            if await self.spicedb.check_permission(
                "campaign", campaign_id, "move", "user", subject_id
            ):
                return True

            # Check individual board token ownership/move permission
            token_id = data.get("token_id") or data.get("tokenId")
            if token_id and await self.spicedb.check_permission(
                "board_token", str(token_id), "move", "user", subject_id
            ):
                return True

            # Check character owner permission if associated
            character_id = data.get("character_id") or data.get("characterId")
            if character_id:
                if await self.spicedb.check_permission(
                    "character", str(character_id), "edit", "user", subject_id
                ):
                    return True
                if await self.spicedb.check_permission(
                    "character", str(character_id), "owner", "user", subject_id
                ):
                    return True
            return False

        # 3. Health modification and condition application authorization
        if action in ("modify_hp", "apply_condition", "clear_condition"):
            character_id = (
                data.get("character_id") or data.get("characterId") or data.get("character")
            )
            if character_id:
                if await self.spicedb.check_permission(
                    "character", str(character_id), "edit", "user", subject_id
                ):
                    return True
                if await self.spicedb.check_permission(
                    "character", str(character_id), "owner", "user", subject_id
                ):
                    return True
            if await self.spicedb.check_permission(
                "campaign", campaign_id, "edit", "user", subject_id
            ):
                return True
            if await self.spicedb.check_permission(
                "campaign", campaign_id, "edit_character", "user", subject_id
            ):
                return True
            return await self.spicedb.check_permission(
                "campaign", campaign_id, action, "user", subject_id
            )

        # 4. DM-restricted encounter and scene mutations
        if action in (
            "spawn_monster",
            "set_scene",
            "spawn_encounter",
            "advance_turn",
            "end_session",
        ):
            # Non-DM rejected (DM check above already passed if authorized)
            return False

        # 5. Default permission check against campaign resource
        return await self.spicedb.check_permission(
            "campaign", campaign_id, action, "user", subject_id
        )


class CampaignWebSocketManager:
    """Manages active live WebSocket connections per campaign."""

    def __init__(self):
        self.active_connections: dict[str, list[tuple[WebSocket, str]]] = {}

    async def connect(self, campaign_id: str, websocket: WebSocket, subject_id: str):
        if campaign_id not in self.active_connections:
            self.active_connections[campaign_id] = []
        self.active_connections[campaign_id].append((websocket, subject_id))

    def disconnect(self, campaign_id: str, websocket: WebSocket):
        if campaign_id in self.active_connections:
            self.active_connections[campaign_id] = [
                (ws, sub) for (ws, sub) in self.active_connections[campaign_id] if ws != websocket
            ]
            if not self.active_connections[campaign_id]:
                del self.active_connections[campaign_id]

    async def broadcast_to_campaign(self, campaign_id: str, message: dict[str, Any]):
        for ws, _ in list(self.active_connections.get(campaign_id, [])):
            with contextlib.suppress(Exception):
                await ws.send_json(message)


ws_campaign_manager = CampaignWebSocketManager()
default_action_validator = WebSocketActionValidator()


def extract_token_from_websocket(websocket: WebSocket) -> str | None:
    """Extract JWT token from WebSocket query parameters or headers."""
    # 1. Query parameters (?token=... or ?access_token=...)
    token = websocket.query_params.get("token") or websocket.query_params.get("access_token")
    if token:
        return token

    # 2. HTTP Authorization header (Bearer ...)
    auth = websocket.headers.get("authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:].strip()

    # 3. Sec-WebSocket-Protocol header (e.g. bearer.<token>)
    protocols = websocket.headers.get("sec-websocket-protocol")
    if protocols:
        for proto in protocols.split(","):
            p = proto.strip()
            if p.startswith("bearer."):
                return p[7:]

    return None


def extract_subject_id(websocket: WebSocket) -> str:
    """Extract authenticated subject identifier from WebSocket query parameters or headers (dev mode fallback)."""
    # 1. Query parameters
    for param in ("user_id", "x_user_id", "subject_id"):
        val = websocket.query_params.get(param)
        if val:
            return val

    # 2. HTTP headers
    x_user = websocket.headers.get("x-user-id")
    if x_user:
        return x_user

    return "guest"


async def campaign_websocket_endpoint(
    websocket: WebSocket,
    campaign_id: str,
    validator: WebSocketActionValidator | None = None,
    auth_service: ZitadelAuthService | None = None,
) -> None:
    """Handle Zanzibar-protected WebSocket connections at /ws/campaigns/{campaign_id}."""
    action_validator = validator or default_action_validator
    service = auth_service or get_zitadel_auth_service()

    token = extract_token_from_websocket(websocket)
    subject_id: str | None = None

    if token:
        try:
            user = service.verify_token(token)
            subject_id = user.user_id
        except Exception as exc:
            logger.warning("WebSocket token verification failed: %s", exc)
            raise HTTPException(
                status_code=401,
                detail=f"Token verification failed: {exc}",
            ) from exc
    elif service.dev_mode:
        subject_id = extract_subject_id(websocket)
    else:
        logger.warning("WebSocket connection rejected: missing token in production mode")
        raise HTTPException(
            status_code=401,
            detail="Authentication required: missing token",
        )

    # 1. On connect: verify viewer/subject has campaign:view or campaign:read permission
    can_connect = await action_validator.validate_connect(campaign_id, subject_id)
    if not can_connect:
        logger.warning(
            "WebSocket connect rejected: subject '%s' lacks view on campaign '%s'",
            subject_id,
            campaign_id,
        )
        await websocket.accept()
        await websocket.send_json(
            {
                "type": "error",
                "code": "PERMISSION_DENIED",
                "message": f"Zanzibar authorization denied: insufficient permissions to view campaign '{campaign_id}'",
                "action": "connect",
            }
        )
        await websocket.close(code=4003, reason="Forbidden: insufficient permissions for campaign")
        return

    await websocket.accept()
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
            allowed = await action_validator.validate_action(campaign_id, subject_id, action, data)
            if not allowed:
                logger.warning(
                    "Zanzibar denied action '%s' for subject '%s' in campaign '%s'",
                    action,
                    subject_id,
                    campaign_id,
                )
                # Immediately respond with PERMISSION_DENIED error frame
                # Do NOT publish the rejected action to Redis or broadcast to other clients
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "PERMISSION_DENIED",
                        "message": f"Zanzibar authorization denied: insufficient permissions for action '{action}'",
                        "action": action,
                    }
                )
                continue

            # 3. Publish authorized event to Redis stream
            stream = (
                "runefoble.events.board"
                if action
                in (
                    "move_token",
                    "board_move",
                    "ghost_preview",
                    "preview_intent",
                    "confirm_intent",
                    "cancel_preview",
                )
                else (
                    "runefoble.events.session"
                    if action in ("modify_hp", "apply_condition", "clear_condition")
                    else "runefoble.events.watcher"
                )
            )
            event_payload = {
                "event_type": f"runefoble.events.{action}",
                "campaign_id": campaign_id,
                "user_id": subject_id,
                "action": action,
                "data": data,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            import gateway_api.main as gw_main

            bus = gw_main.get_event_bus()
            if bus is not None:
                with contextlib.suppress(Exception):
                    await bus.publish_event(stream, event_payload)

            # 4. Broadcast state to connected party clients
            broadcast_payload = {
                "type": data.get("type", action),
                "action": action,
                "status": "applied",
                "campaign_id": campaign_id,
                "user_id": subject_id,
                **{k: v for k, v in data.items() if k not in ("type", "action")},
            }
            await ws_campaign_manager.broadcast_to_campaign(campaign_id, broadcast_payload)

    except WebSocketDisconnect:
        ws_campaign_manager.disconnect(campaign_id, websocket)
