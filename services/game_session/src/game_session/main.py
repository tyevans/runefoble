"""Game Session Microservice entrypoint - Powered by eventsource-py.

Coordinates active sessions, participant presence, turn order, and campaign timelines.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from game_session.campaign import campaign_router, register_campaign_error_handlers
from game_session.dependencies import (
    event_bus_provider,
    get_event_bus,
    get_spicedb_client,
    repo,
    set_event_bus,
    set_spicedb_client,
)
from game_session.profile import profile_router
from game_session.routers import (
    autopilot_router,
    bounties_router,
    campfire_router,
    caravan_contracts_router,
    caravan_trade_router,
    chronicle_router,
    combat_router,
    director_router,
    minigames_ws_router,
    reactions_router,
    session_router,
    settlements_router,
    stronghold_router,
    tavern_router,
    west_marches_router,
)
from game_session.settlement.haggling_router import router as settlement_haggling_router
from game_session.settlement.router import router as settlement_haven_router
from game_session.settlement.workers_router import router as settlement_workers_router
from runefoble_auth.authz_http import install_authz_error_handlers
from runefoble_platform.aggregate_loading import register_store_unavailable_handlers
from runefoble_platform.event_publish import (
    event_publish_failures,
    install_publish_failure_handler,
)
from runefoble_platform.event_sourcing import event_store_kind, get_event_store
from runefoble_platform.ui_manifest import load_ui_manifest

# Start-up fails when the manifest is missing or invalid. No fallback manifest exists (ADR-0015 4).
UI_MANIFEST = load_ui_manifest(
    Path(__file__).resolve().parent.parent.parent / "ui" / "manifest.json"
)

__all__ = [
    "app",
    "get_event_bus",
    "get_spicedb_client",
    "repo",
    "set_event_bus",
    "set_spicedb_client",
]

# Build the event store now. A deployed service without a reachable store refuses to start (TASK-0707).
get_event_store()

app = FastAPI(
    title="Runefoble - Game Session Service",
    version="0.1.0",
    description="Session Lifecycle, Turn / Initiative Order, and Live Participation backed by eventsource-py.",
    lifespan=event_bus_provider.lifespan,
)

register_store_unavailable_handlers(app)
app.include_router(session_router)
app.include_router(campaign_router)
register_campaign_error_handlers(app)
app.include_router(combat_router)
app.include_router(director_router)
app.include_router(reactions_router)
app.include_router(autopilot_router)
app.include_router(campfire_router)
app.include_router(stronghold_router)
app.include_router(tavern_router)
app.include_router(minigames_ws_router)
app.include_router(west_marches_router)
app.include_router(caravan_trade_router)
app.include_router(chronicle_router)
app.include_router(caravan_contracts_router)
app.include_router(settlements_router)
app.include_router(settlements_router, prefix="/api/v1")
app.include_router(settlement_haven_router)
app.include_router(settlement_workers_router)
app.include_router(settlement_haggling_router)
app.include_router(bounties_router)
app.include_router(bounties_router, prefix="/api/v1")
app.include_router(profile_router)
install_publish_failure_handler(app)
install_authz_error_handlers(app)


@app.get("/healthz")
async def health_check():
    return {
        "status": "ok",
        "service": "game_session",
        "event_store": event_store_kind(),
        "event_publish_failures": event_publish_failures(),
    }


@app.get("/ui/manifest")
@app.get("/game_session/ui/manifest")
def get_ui_manifest():
    """Advertise vendored microfrontend components for game session."""
    return UI_MANIFEST


def main():
    import uvicorn

    uvicorn.run("game_session.main:app", host="0.0.0.0", port=8004, reload=True)


if __name__ == "__main__":
    main()

__all__ = [
    "app",
    "get_event_bus",
    "main",
    "repo",
    "set_event_bus",
]
