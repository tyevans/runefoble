"""Board State Microservice - Powered by eventsource-py.

Manages tactical maps, token coordinates, collision rules, kinematics, and fog-of-war.
"""

from __future__ import annotations

from board_state.dependencies import BoardNotFoundError, event_bus_provider
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
    ui_manifest_router,
    uvtt_import_router,
    vfx_router,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from runefoble_auth.authz_http import install_authz_error_handlers
from runefoble_platform.event_publish import (
    event_publish_failures,
    install_publish_failure_handler,
)
from runefoble_platform.event_sourcing import event_store_kind, get_event_store

# Build the event store now. A deployed service without a reachable store refuses to start (TASK-0707).
get_event_store()

app = FastAPI(
    title="Runefoble - Board State Service",
    version="0.1.0",
    description="Tactical Map, Grid Coordinates, Token Management, and Spatial Queries backed by eventsource-py.",
    lifespan=event_bus_provider.lifespan,
)

app.include_router(ui_manifest_router)
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


@app.exception_handler(BoardNotFoundError)
async def board_not_found_handler(request: Request, exc: BoardNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.get("/healthz")
async def health_check():
    return {
        "status": "ok",
        "service": "board_state",
        "event_publish_failures": event_publish_failures(),
        "event_store": event_store_kind(),
    }


def main():
    import uvicorn

    uvicorn.run("board_state.main:app", host="0.0.0.0", port=8002, reload=True)


if __name__ == "__main__":
    main()
