"""Runefoble API Gateway.

Aggregates downstream microservices, exposes unified OpenAPI documentation,
enforces fine-grained SpiceDB Zanzibar object authorization, and powers
real-time WebSockets for the tactical board and voice chronicle.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from game_session.settlement.router import router as settlement_haven_router
from gateway_api.assets import router as assets_router
from gateway_api.auth import get_zitadel_auth_service
from gateway_api.auth_sync import router as auth_sync_router
from gateway_api.dependencies import (
    WebSocketConnectionManager,
    get_event_bus,
    platform_settings,
    set_event_bus,
    ws_manager,
)
from gateway_api.mobile_companion import (
    mobile_companion_websocket_endpoint,
)
from gateway_api.mobile_companion import (
    router as companion_router,
)
from gateway_api.routers import (
    auth_router,
    campaigns_router,
    characters_router,
    downtime_router,
    health_router,
    hub_views_router,
    overlay_router,
    sessions_router,
    soundscape_router,
    spectator_router,
)
from gateway_api.upstream_errors import register_upstream_error_handlers
from gateway_api.upstreams import UpstreamRegistry
from gateway_api.webrtc_signaling import voice_signaling_websocket_endpoint
from gateway_api.websocket import campaign_websocket_endpoint
from gateway_api.websocket_auth import admit_gateway_websocket
from gateway_mcp.dynamic import set_event_bus as set_dynamic_tool_event_bus
from gateway_mcp.routers import tools_registry_router
from runefoble_platform.config import PlatformSettings
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.telemetry import init_telemetry
from voice_agent.room_routes import router as voice_rooms_router
from voice_agent.routers.stream_diagnostics import router as stream_diagnostics_router


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build the upstream service clients from settings at start-up. Close them at shutdown."""
    app.state.upstreams = UpstreamRegistry.from_settings(PlatformSettings())
    try:
        yield
    finally:
        await app.state.upstreams.aclose()


app = FastAPI(
    title="Runefoble Platform Unified Gateway",
    version="0.1.0",
    description="Unified API & OpenAPI Hub for Runefoble: Collaborative AI Tabletop Roleplaying.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=_lifespan,
)
register_upstream_error_handlers(app)

_cors_origins = [o.strip() for o in platform_settings.cors_origins.split(",") if o.strip()]
if "*" in _cors_origins:
    raise RuntimeError("RUNEFOBLE_CORS_ORIGINS must list explicit origins. '*' is refused.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(campaigns_router)
app.include_router(sessions_router)
app.include_router(hub_views_router)
app.include_router(characters_router)
app.include_router(downtime_router)
app.include_router(settlement_haven_router)
app.include_router(spectator_router)
app.include_router(overlay_router)
app.include_router(soundscape_router)
app.include_router(assets_router, prefix="/api/v1/assets", tags=["Assets"])
app.include_router(auth_sync_router, prefix="/api/v1/auth/sync", tags=["Auth Sync"])
app.include_router(voice_rooms_router)
app.include_router(companion_router)
app.include_router(stream_diagnostics_router)
app.include_router(tools_registry_router)
app.include_router(tools_registry_router, prefix="/api/v1")


init_telemetry("gateway-api", settings=platform_settings, app=app)


def configure_dynamic_tool_event_bus(redis_url: str) -> RedisStreamsEventBus:
    """Inject the Redis Streams bus that dynamic MCP tool events publish to.

    Raises RuntimeError when no Redis URL is configured, so the gateway never
    runs dynamic tools with events that cannot reach the system stream.
    """
    if not redis_url:
        raise RuntimeError("REDIS_URL must be set: dynamic MCP tool events require Redis Streams")
    bus = RedisStreamsEventBus(redis_url=redis_url)
    set_dynamic_tool_event_bus(bus)
    return bus


configure_dynamic_tool_event_bus(platform_settings.redis_url)


@app.websocket("/ws/campaigns/{campaign_id}")
async def campaign_websocket(websocket: WebSocket, campaign_id: str) -> None:
    """Zanzibar-protected real-time WebSocket stream for campaign mutations."""
    await campaign_websocket_endpoint(websocket, campaign_id)


@app.websocket("/ws/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str) -> None:
    """Realtime stream connecting board, voice, and Watcher chronicle."""
    if await admit_gateway_websocket(websocket) is None:
        return
    ws_manager.register(websocket)
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


@app.websocket("/ws/mobile-companion/{session_id}")
async def mobile_companion_websocket(websocket: WebSocket, session_id: str) -> None:
    """Zanzibar-protected low-bandwidth mobile WebRTC companion and haptic gateway."""
    await mobile_companion_websocket_endpoint(websocket, session_id)


@app.websocket("/ws/establishments/{establishment_id}/tables/{table_id}")
async def gateway_establishment_table_ws(
    websocket: WebSocket,
    establishment_id: str,
    table_id: str,
) -> None:
    """Establishment-scoped multiplayer minigame table WebSocket channel via gateway."""
    from game_session.routers.minigames_ws import handle_table_websocket

    await handle_table_websocket(websocket, table_id, establishment_id, get_zitadel_auth_service())


@app.websocket("/ws/minigames/{table_id}")
async def gateway_standalone_minigame_ws(
    websocket: WebSocket,
    table_id: str,
) -> None:
    """Standalone multiplayer minigame table WebSocket channel via gateway."""
    from game_session.routers.minigames_ws import handle_table_websocket

    await handle_table_websocket(websocket, table_id, "est-default", get_zitadel_auth_service())


def main() -> None:
    import os

    import uvicorn

    host = os.environ.get("GATEWAY_HOST", "0.0.0.0")
    port = int(os.environ.get("GATEWAY_PORT", os.environ.get("PORT", "8000")))
    uvicorn.run("gateway_api.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()

__all__ = [
    "WebSocketConnectionManager",
    "app",
    "configure_dynamic_tool_event_bus",
    "get_event_bus",
    "platform_settings",
    "set_event_bus",
    "ws_manager",
]
