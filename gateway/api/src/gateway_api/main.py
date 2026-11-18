"""Runefoble API Gateway.

Aggregates downstream microservices, exposes unified OpenAPI documentation,
enforces fine-grained SpiceDB Zanzibar object authorization, and powers
real-time WebSockets for the tactical board and voice chronicle.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from gateway_api.assets import router as assets_router
from gateway_api.auth_sync import router as auth_sync_router
from gateway_api.companion import companion_router, mobile_companion_websocket_endpoint
from gateway_api.dependencies import (
    event_bus_provider,
    get_event_bus,
    platform_settings,
    set_event_bus,
)
from gateway_api.routers import (
    auth_router,
    boards_router,
    campaigns_router,
    characters_router,
    compendium_router,
    downtime_router,
    health_router,
    hub_views_router,
    lore_views_router,
    overlay_router,
    sessions_router,
    soundscape_router,
    spectator_router,
)
from gateway_api.routers.settlements_proxy import router as settlements_router
from gateway_api.session_websocket import session_websocket_endpoint
from gateway_api.signaling import voice_signaling_websocket_endpoint
from gateway_api.upstream_errors import register_upstream_error_handlers
from gateway_api.upstreams import UpstreamRegistry
from gateway_api.websocket_endpoint import campaign_websocket_endpoint
from gateway_api.websocket_relay import relay_websocket
from runefoble_auth.authz_http import install_authz_error_handlers
from runefoble_platform.config import PlatformSettings
from runefoble_platform.telemetry import init_telemetry
from voice_agent.room_routes import router as voice_rooms_router
from voice_agent.routers.stream_diagnostics import router as stream_diagnostics_router


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build the upstream service clients from settings at start-up. Close them at shutdown."""
    app.state.upstreams = UpstreamRegistry.from_settings(PlatformSettings())
    try:
        async with event_bus_provider.lifespan(app):
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
install_authz_error_handlers(app)

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
app.include_router(boards_router)
app.include_router(sessions_router)
app.include_router(hub_views_router)
app.include_router(lore_views_router)
app.include_router(characters_router)
app.include_router(compendium_router)
app.include_router(downtime_router)
app.include_router(settlements_router)
app.include_router(spectator_router)
app.include_router(overlay_router)
app.include_router(soundscape_router)
app.include_router(assets_router, prefix="/api/v1/assets", tags=["Assets"])
app.include_router(auth_sync_router, prefix="/api/v1/auth/sync", tags=["Auth Sync"])
app.include_router(voice_rooms_router)
app.include_router(companion_router)
app.include_router(stream_diagnostics_router)


init_telemetry("gateway-api", settings=platform_settings, app=app)


@app.websocket("/ws/campaigns/{campaign_id}")
async def campaign_websocket(websocket: WebSocket, campaign_id: str) -> None:
    """Zanzibar-protected real-time WebSocket stream for campaign mutations."""
    await campaign_websocket_endpoint(websocket, campaign_id)


@app.websocket("/ws/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str) -> None:
    """Realtime stream connecting board, voice, and Watcher chronicle."""
    await session_websocket_endpoint(websocket, session_id)


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
    """Establishment-scoped minigame table socket. game_session owns it; the gateway relays frames."""
    await relay_websocket(
        websocket,
        service="game_session",
        segments=("ws", "establishments", establishment_id, "tables", table_id),
    )


@app.websocket("/ws/minigames/{table_id}")
async def gateway_standalone_minigame_ws(
    websocket: WebSocket,
    table_id: str,
) -> None:
    """Standalone minigame table socket. game_session owns it; the gateway relays frames."""
    await relay_websocket(websocket, service="game_session", segments=("ws", "minigames", table_id))


def main() -> None:
    import os

    import uvicorn

    host = os.environ.get("GATEWAY_HOST", "0.0.0.0")
    port = int(os.environ.get("GATEWAY_PORT", os.environ.get("PORT", "8000")))
    uvicorn.run("gateway_api.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()

__all__ = [
    "app",
    "get_event_bus",
    "platform_settings",
    "set_event_bus",
]
