"""Runefoble API Gateway.

Aggregates downstream microservices, exposes unified OpenAPI documentation,
and powers real-time WebSockets for the tactical board and voice chronicle.
A proxy route forwards the caller's token, and the owning service checks the
object permission (ADR-0001). A composite route, which combines several owner
reads, checks the permission at the gateway. The proxy routes that keep a gateway
check are listed in the call-owning-services how-to guide (TASK-0845).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from gateway_api.account_invite_limits import build_account_invite_limits
from gateway_api.auth_sync import router as auth_sync_router
from gateway_api.cors import install_cors
from gateway_api.dependencies import event_bus_provider, get_event_bus, platform_settings
from gateway_api.routers import (
    analytics_views_router,
    auth_router,
    boards_router,
    campaigns_router,
    characters_router,
    compendium_router,
    downtime_router,
    health_router,
    lore_views_router,
    overlay_router,
    sessions_router,
    soundscape_router,
    spectator_router,
    voice_proxy_router,
)
from gateway_api.routers.account_invites_proxy import router as account_invites_router
from gateway_api.routers.assets_proxy import router as assets_router
from gateway_api.routers.audience import router as audience_router
from gateway_api.routers.caravan_proxy import router as caravan_router
from gateway_api.routers.characters_wardrobe_proxy import router as wardrobe_router
from gateway_api.routers.forge_proxy import router as forge_router
from gateway_api.routers.health import readiness_gate
from gateway_api.routers.realtime import router as realtime_router
from gateway_api.routers.settlements_proxy import router as settlements_router
from gateway_api.routers.watcher_proxy_dm import router as watcher_dm_router
from gateway_api.routers.watcher_proxy_factions import router as watcher_factions_router
from gateway_api.routers.watcher_proxy_intent import router as watcher_intent_router
from gateway_api.routers.watcher_speech_proxy import router as watcher_speech_router
from gateway_api.session_frame_consumer import SESSION_FRAMES, start_session_frame_consumers
from gateway_api.upstream_errors import register_upstream_error_handlers
from gateway_api.upstreams import UpstreamRegistry
from runefoble_auth.authz_http import install_authz_error_handlers
from runefoble_platform.config import PlatformSettings
from runefoble_platform.readiness import set_readiness_gate
from runefoble_platform.telemetry import init_telemetry


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build the upstream clients and start the session frame consumer. Stop both at shutdown."""
    app.state.upstreams = UpstreamRegistry.from_settings(PlatformSettings())
    app.state.account_invite_limits = build_account_invite_limits()
    set_readiness_gate(app, readiness_gate())
    try:
        async with event_bus_provider.lifespan(app):
            consumers = await start_session_frame_consumers(get_event_bus())
            app.state.consumers = {SESSION_FRAMES: consumers}
            try:
                yield
            finally:
                await consumers.stop()
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

install_cors(app, platform_settings.cors_origins)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(campaigns_router)
app.include_router(account_invites_router)
app.include_router(boards_router)
app.include_router(sessions_router)
app.include_router(analytics_views_router)
app.include_router(lore_views_router)
app.include_router(characters_router)
app.include_router(wardrobe_router)
app.include_router(compendium_router)
app.include_router(downtime_router)
app.include_router(settlements_router)
app.include_router(spectator_router)
app.include_router(overlay_router)
app.include_router(soundscape_router)
app.include_router(assets_router)
app.include_router(forge_router)
app.include_router(caravan_router)
app.include_router(audience_router)
app.include_router(auth_sync_router, prefix="/api/v1/auth/sync", tags=["Auth Sync"])
app.include_router(voice_proxy_router)
app.include_router(watcher_speech_router)
app.include_router(watcher_intent_router)
app.include_router(watcher_dm_router)
app.include_router(watcher_factions_router)
app.include_router(realtime_router)


init_telemetry("gateway-api", settings=platform_settings, app=app)


def main() -> None:
    import os

    import uvicorn

    host = os.environ.get("GATEWAY_HOST", "0.0.0.0")
    port = int(os.environ.get("GATEWAY_PORT", os.environ.get("PORT", "8000")))
    uvicorn.run("gateway_api.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()
