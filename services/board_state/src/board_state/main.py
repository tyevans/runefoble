"""Board State Microservice - Powered by eventsource-py.

Manages tactical maps, token coordinates, collision rules, kinematics, and fog-of-war.
"""

from __future__ import annotations

from board_state.dependencies import (
    get_event_bus,
    get_or_create_board,
    repo,
    set_event_bus,
    to_board_uuid,
)
from board_state.models import (
    ConfigureTerrainRequest,
    CreateBoardRequest,
    FogOfWarUpdateRequest,
    MoveTokenRequest,
    MoveTokenResponse,
    PlaceTokenRequest,
    UVTTImportResponse,
    VisibilityResponse,
)
from board_state.routers import (
    boards_router,
    previews_router,
    terrain_router,
    tokens_router,
    vfx_router,
)
from board_state.routers.boards import get_ui_manifest
from fastapi import FastAPI
from runefoble_platform.event_sourcing import get_event_store

app = FastAPI(
    title="Runefoble - Board State Service",
    version="0.1.0",
    description="Tactical Map, Grid Coordinates, Token Management, and Spatial Queries backed by eventsource-py.",
)

app.include_router(boards_router)
app.include_router(tokens_router)
app.include_router(terrain_router)
app.include_router(previews_router)
app.include_router(vfx_router)


@app.get("/healthz")
async def health_check():
    return {
        "status": "ok",
        "service": "board_state",
        "event_store": type(get_event_store()).__name__,
    }


def main():
    import uvicorn

    uvicorn.run("board_state.main:app", host="0.0.0.0", port=8002, reload=True)


if __name__ == "__main__":
    main()

__all__ = [
    "ConfigureTerrainRequest",
    "CreateBoardRequest",
    "FogOfWarUpdateRequest",
    "MoveTokenRequest",
    "MoveTokenResponse",
    "PlaceTokenRequest",
    "UVTTImportResponse",
    "VisibilityResponse",
    "app",
    "get_event_bus",
    "get_or_create_board",
    "get_ui_manifest",
    "main",
    "repo",
    "set_event_bus",
    "to_board_uuid",
]
