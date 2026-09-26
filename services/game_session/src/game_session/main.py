"""Game Session Microservice entrypoint - Powered by eventsource-py.

Coordinates active sessions, participant presence, turn order, and campaign timelines.
"""

from __future__ import annotations

from fastapi import FastAPI
from game_session.dependencies import (
    get_event_bus,
    get_spicedb_client,
    repo,
    set_event_bus,
    set_spicedb_client,
)
from game_session.routers import (
    autopilot_router,
    combat_router,
    session_router,
)
from runefoble_platform.event_sourcing import get_event_store

__all__ = [
    "app",
    "get_event_bus",
    "get_spicedb_client",
    "repo",
    "set_event_bus",
    "set_spicedb_client",
]

app = FastAPI(
    title="Runefoble - Game Session Service",
    version="0.1.0",
    description="Session Lifecycle, Turn / Initiative Order, and Live Participation backed by eventsource-py.",
)

app.include_router(session_router)
app.include_router(combat_router)
app.include_router(autopilot_router)


@app.get("/healthz")
async def health_check():
    return {
        "status": "ok",
        "service": "game_session",
        "event_store": type(get_event_store()).__name__,
    }


@app.get("/ui/manifest")
def get_ui_manifest():
    """Advertise vendored microfrontend components for game session."""
    return {
        "service": "game_session",
        "package": "@runefoble/game-session-ui",
        "components": [
            "runefoble-initiative-tracker",
            "runefoble-dice-roller",
            "runefoble-spectator-view",
        ],
        "version": "0.1.0",
    }


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
