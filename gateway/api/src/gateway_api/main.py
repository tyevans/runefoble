"""Runefoble API Gateway.

Aggregates downstream microservices, exposes unified OpenAPI documentation,
enforces fine-grained SpiceDB Zanzibar object authorization, and powers
real-time WebSockets for the tactical board and voice chronicle.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from gateway_api.assets import router as assets_router
from gateway_api.auth_sync import router as auth_sync_router
from gateway_api.dependencies import (
    WebSocketConnectionManager,
    get_event_bus,
    platform_settings,
    set_event_bus,
    ws_manager,
)
from gateway_api.routers import campaigns_router, health_router, spectator_router
from gateway_api.webrtc_signaling import voice_signaling_websocket_endpoint
from gateway_api.websocket import campaign_websocket_endpoint
from gateway_mcp.dynamic_registry import router as mcp_tools_router
from runefoble_platform.telemetry import init_telemetry
from voice_agent.room_routes import router as voice_rooms_router

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

app.include_router(health_router)
app.include_router(campaigns_router)
app.include_router(spectator_router)
app.include_router(assets_router, prefix="/api/v1/assets", tags=["Assets"])
app.include_router(auth_sync_router, prefix="/api/v1/auth/sync", tags=["Auth Sync"])
app.include_router(voice_rooms_router)
app.include_router(mcp_tools_router)
app.include_router(mcp_tools_router, prefix="/api/v1")


init_telemetry("gateway-api", settings=platform_settings, app=app)


@app.websocket("/ws/campaigns/{campaign_id}")
async def campaign_websocket(websocket: WebSocket, campaign_id: str) -> None:
    """Zanzibar-protected real-time WebSocket stream for campaign mutations."""
    await campaign_websocket_endpoint(websocket, campaign_id)


@app.websocket("/ws/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str) -> None:
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


@app.websocket("/ws/voice/{session_id}")
async def voice_websocket(websocket: WebSocket, session_id: str) -> None:
    """Zanzibar-protected WebRTC live voice room signaling stream."""
    await voice_signaling_websocket_endpoint(websocket, session_id)


def main() -> None:
    import uvicorn

    uvicorn.run("gateway_api.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()

__all__ = [
    "WebSocketConnectionManager",
    "app",
    "get_event_bus",
    "platform_settings",
    "set_event_bus",
    "ws_manager",
]
