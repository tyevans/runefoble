"""Board State Microservice - Powered by eventsource-py.

Manages tactical maps, token coordinates, collision rules, kinematics, and fog-of-war.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from pathlib import Path

from board_state.dependencies import event_bus_provider
from board_state.forged_battlemap import start_board_consumers
from board_state.routers import (
    actions_router,
    aoe_router,
    boards_router,
    camera_router,
    physics_router,
    previews_http_router,
    previews_ws_router,
    spectator_router,
    terrain_router,
    tokens_router,
    traps_router,
    uvtt_import_router,
    vfx_router,
)
from fastapi import FastAPI, Request
from runefoble_auth.authz_http import install_authz_error_handlers
from runefoble_platform.aggregate_loading import register_store_unavailable_handlers
from runefoble_platform.domain_errors_http import install_domain_error_handlers
from runefoble_platform.event_publish import (
    event_publish_failures,
    install_publish_failure_handler,
)
from runefoble_platform.event_sourcing import event_store_kind, get_event_store
from runefoble_platform.storage import get_storage_service
from runefoble_platform.stream_consumer import consumer_statuses
from runefoble_platform.ui_manifest import ui_manifest_router


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open the Redis Streams bus and start the forged battlemap consumer."""
    # A deployed service without the Silo keys refuses to start (TASK-0926).
    get_storage_service()
    bus = await event_bus_provider.connect()
    consumers = await start_board_consumers(bus)
    app.state.consumers = {"board_state": consumers}
    try:
        yield
    finally:
        await consumers.stop()
        await event_bus_provider.close()
        app.state.consumers = {}


# Build the event store now. A deployed service without a reachable store refuses to start (TASK-0707).
get_event_store()

app = FastAPI(
    title="Runefoble - Board State Service",
    version="0.1.0",
    description="Tactical Map, Grid Coordinates, Token Management, and Spatial Queries backed by eventsource-py.",
    lifespan=lifespan,
)

app.include_router(
    ui_manifest_router(
        Path(__file__).resolve().parents[2] / "ui" / "manifest.json",
        summary="Advertise vendored microfrontend components for board state",
    )
)
app.include_router(boards_router)
app.include_router(spectator_router)
app.include_router(camera_router)
app.include_router(tokens_router)
app.include_router(terrain_router)
app.include_router(previews_http_router)
app.include_router(previews_ws_router)
app.include_router(actions_router)
app.include_router(aoe_router)
app.include_router(vfx_router)
app.include_router(physics_router)
app.include_router(traps_router)
app.include_router(uvtt_import_router)
install_publish_failure_handler(app)
install_authz_error_handlers(app)
register_store_unavailable_handlers(app)
install_domain_error_handlers(app)


@app.get("/healthz")
async def health_check(request: Request):
    return {
        "status": "ok",
        "service": "board_state",
        "consumers": consumer_statuses(getattr(request.app.state, "consumers", {})),
        "event_publish_failures": event_publish_failures(),
        "event_store": event_store_kind(),
    }


def main():
    import uvicorn

    uvicorn.run("board_state.main:app", host="0.0.0.0", port=8002, reload=True)


if __name__ == "__main__":
    main()
