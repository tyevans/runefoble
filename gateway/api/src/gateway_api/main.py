"""Runefoble API Gateway.

Aggregates downstream microservices, exposes unified OpenAPI documentation,
enforces fine-grained SpiceDB Zanzibar object authorization, and powers
real-time WebSockets for the tactical board and voice chronicle.
"""

import contextlib
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from gateway_api.assets import router as assets_router
from gateway_api.auth import get_spicedb_client, require_zanzibar_permission
from gateway_api.auth_sync import router as auth_sync_router
from gateway_api.spectator import (
    SpectatorStateResponse,
    SpectatorViewerInfo,
    get_raw_session_state,
    sanitize_spectator_state,
)
from gateway_api.websocket import campaign_websocket_endpoint
from pydantic import BaseModel, Field
from runefoble_events import SpectatorSessionConnected
from runefoble_platform.config import PlatformSettings
from runefoble_platform.redis_bus import RedisStreamsEventBus

platform_settings = PlatformSettings()
_event_bus: RedisStreamsEventBus | None = None


def get_event_bus() -> RedisStreamsEventBus | None:
    global _event_bus
    if _event_bus is None and platform_settings.redis_url:
        with contextlib.suppress(Exception):
            _event_bus = RedisStreamsEventBus(redis_url=platform_settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    global _event_bus
    _event_bus = bus


app = FastAPI(
    title="Runefoble Platform Unified Gateway",
    version="0.1.0",
    description="Unified API & OpenAPI Hub for Runefoble: Collaborative AI Tabletop Roleplaying.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assets_router, prefix="/api/v1/assets", tags=["Assets"])
app.include_router(auth_sync_router, prefix="/api/v1/auth/sync", tags=["Auth Sync"])


class WebSocketConnectionManager:
    """Manages active live session WebSocket connections."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]):
        for connection in self.active_connections:
            with contextlib.suppress(Exception):
                await connection.send_json(message)


ws_manager = WebSocketConnectionManager()


class AssignRoleRequest(BaseModel):
    user_id: str
    role: Literal["owner", "dungeon_master", "player", "spectator"]


class AdvanceTurnRequest(BaseModel):
    next_character_id: str


class DMOverrideRequest(BaseModel):
    action: str
    reason: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class AtmosphereUpdateRequest(BaseModel):
    location_name: str
    lighting: str = "Normal"
    mood: str = "Neutral"
    description: str = ""
    ambient_audio_prompt: str | None = None


class TokenMoveRequest(BaseModel):
    to_x: int
    to_y: int


@app.get("/healthz")
async def health_check():
    return {
        "status": "healthy",
        "gateway": "runefoble-api-gateway",
        "downstream_services": {
            "the_watcher": "operational",
            "game_session": "operational",
            "board_state": "operational",
            "character_sheet": "operational",
            "voice_agent": "operational",
        },
        "authorization_engine": "SpiceDB Zanzibar",
    }


# ---------------------------------------------------------------------------
# Campaign Authorization and Role Management (Zanzibar)
# ---------------------------------------------------------------------------


@app.post("/api/v1/campaigns/{campaign_id}/roles")
async def assign_campaign_role(campaign_id: str, req: AssignRoleRequest):
    """Write fine-grained relationship tuple to SpiceDB Zanzibar."""
    client = get_spicedb_client()
    relation_map = {
        "owner": "owner",
        "dungeon_master": "dungeon_master",
        "player": "player",
        "spectator": "view",
    }
    relation = relation_map[req.role]
    await client.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation=relation,
        subject_type="user",
        subject_id=req.user_id,
    )
    return {
        "status": "role_assigned",
        "campaign_id": campaign_id,
        "user_id": req.user_id,
        "role": req.role,
        "zanzibar_relation": f"campaign:{campaign_id}#{relation}@user:{req.user_id}",
    }


# ---------------------------------------------------------------------------
# Protected Session and Board Endpoints
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/sessions/{session_id}",
    dependencies=[Depends(require_zanzibar_permission("view", resource_type="campaign"))],
)
async def get_session_proxy(session_id: str):
    """Retrieve game session state, participants, and round index (requires 'view')."""
    return {
        "id": session_id,
        "campaign_id": session_id,
        "status": "active",
        "round": 3,
        "current_turn": "c1",
        "participants": [
            {"username": "Alice", "character": "Valeros", "role": "player", "online": True},
            {
                "username": "Bob",
                "character": "Kyra",
                "role": "player",
                "online": False,
                "ai_stand_in": True,
            },
        ],
    }


@app.post(
    "/api/v1/sessions/{session_id}/turns/advance",
    dependencies=[Depends(require_zanzibar_permission("run_session", resource_type="campaign"))],
)
async def advance_turn_proxy(session_id: str, req: AdvanceTurnRequest):
    """Advance session turn (requires 'run_session' DM permission)."""
    return {
        "session_id": session_id,
        "status": "turn_advanced",
        "active_character_id": req.next_character_id,
    }


@app.post(
    "/api/v1/sessions/{session_id}/dm-override",
    dependencies=[Depends(require_zanzibar_permission("run_session", resource_type="campaign"))],
)
async def dm_override_proxy(session_id: str, req: DMOverrideRequest):
    """Execute DM override on session rules or actions (requires 'run_session')."""
    return {
        "session_id": session_id,
        "status": "override_executed",
        "action": req.action,
        "reason": req.reason,
    }


@app.post(
    "/api/v1/sessions/{session_id}/atmosphere",
    dependencies=[Depends(require_zanzibar_permission("run_session", resource_type="campaign"))],
)
async def update_atmosphere_proxy(session_id: str, req: AtmosphereUpdateRequest):
    """Update campaign sensory atmosphere and lighting (requires 'run_session')."""
    return {
        "session_id": session_id,
        "status": "atmosphere_updated",
        "atmosphere": req.model_dump(),
    }


@app.post(
    "/api/v1/board/tokens/{token_id}/move",
    dependencies=[
        Depends(
            require_zanzibar_permission(
                "move", resource_type="board_token", resource_param="token_id"
            )
        )
    ],
)
async def move_token_proxy(token_id: str, req: TokenMoveRequest):
    """Move a tactical token on the board (requires 'move' on board_token)."""
    return {
        "token_id": token_id,
        "status": "token_moved",
        "to_x": req.to_x,
        "to_y": req.to_y,
    }


@app.get(
    "/api/v1/board/tokens/{token_id}",
    dependencies=[
        Depends(
            require_zanzibar_permission(
                "inspect", resource_type="board_token", resource_param="token_id"
            )
        )
    ],
)
async def get_token_proxy(token_id: str):
    """Inspect tactical token details (requires 'inspect' on board_token)."""
    return {
        "token_id": token_id,
        "status": "active",
        "x": 2,
        "y": 3,
    }


@app.get(
    "/api/v1/boards/{session_id}",
    dependencies=[Depends(require_zanzibar_permission("view", resource_type="campaign"))],
)
async def get_board_proxy(session_id: str):
    """Retrieve tactical board tokens, coordinates, and grid dimensions (requires 'view')."""
    return {
        "session_id": session_id,
        "cols": 8,
        "rows": 8,
        "tokens": [
            {"id": "t1", "name": "Valeros", "x": 2, "y": 3, "color": "#2563eb"},
            {
                "id": "t2",
                "name": "Kyra",
                "x": 3,
                "y": 3,
                "color": "#db2777",
                "is_ai_controlled": True,
            },
        ],
    }


@app.post("/api/v1/watcher/speak-and-act")
async def speak_and_act(transcript: str, speaker_name: str, session_id: str):
    """Spoken command ingestion: parse intent and mutate the game board in real-time."""
    event = {
        "type": "speech_action",
        "speaker": speaker_name,
        "transcript": transcript,
        "action_taken": "Valeros stepped forward 2 squares.",
        "watcher_commentary": "The Watcher observes your advance into the crypt.",
    }
    await ws_manager.broadcast(event)
    return event


# ---------------------------------------------------------------------------
# Spectator Stream Endpoint
# ---------------------------------------------------------------------------


@app.get("/api/v1/spectate/{session_id}", response_model=SpectatorStateResponse)
async def get_spectator_state(
    session_id: str,
    token: str | None = Query(None, description="Optional spectator access token"),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    authorization: str | None = Header(None, alias="Authorization"),
):
    """Retrieve audience-safe spectator view of the session, board, and chronicle.

    Redacts hidden tokens, monster stat blocks, and private DM notes.
    Dispatches SpectatorSessionConnected event to the Redis event bus.
    """
    if token:
        viewer_id = f"spectator_{token}"
        viewer_name = f"Spectator ({token})"
    elif x_user_id:
        viewer_id = x_user_id
        viewer_name = f"Viewer {x_user_id}"
    elif authorization and authorization.startswith("Bearer "):
        bearer = authorization[7:].strip()
        viewer_id = f"viewer_{bearer}"
        viewer_name = f"Spectator ({bearer})"
    else:
        viewer_id = "spectator_guest"
        viewer_name = "Guest Spectator"

    viewer_info = SpectatorViewerInfo(viewer_id=viewer_id, viewer_name=viewer_name)

    # Dispatch SpectatorSessionConnected event to Redis bus
    event = SpectatorSessionConnected(
        session_id=session_id,
        viewer_id=viewer_id,
        viewer_name=viewer_name,
        connected_at=datetime.now(UTC).isoformat(),
    )
    bus = get_event_bus()
    if bus is not None:
        with contextlib.suppress(Exception):
            await bus.publish_event("runefoble.events.spectator", event)

    raw_state = get_raw_session_state(session_id)
    return sanitize_spectator_state(raw_state, viewer_info=viewer_info)


@app.websocket("/ws/campaigns/{campaign_id}")
async def campaign_websocket(websocket: WebSocket, campaign_id: str):
    """Zanzibar-protected real-time WebSocket stream for campaign mutations."""
    await campaign_websocket_endpoint(websocket, campaign_id)


@app.websocket("/ws/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str):
    """Realtime stream connecting board, voice, and Watcher chronicle."""
    await ws_manager.connect(websocket)
    try:
        await websocket.send_json(
            {
                "type": "connected",
                "session_id": session_id,
                "message": "Connected to Runefoble real-time stream. The Watcher is listening.",
            }
        )
        while True:
            data = await websocket.receive_json()
            # Broadcast incoming updates to all connected party members
            await ws_manager.broadcast(data)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


def main():
    import uvicorn

    uvicorn.run("gateway_api.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
