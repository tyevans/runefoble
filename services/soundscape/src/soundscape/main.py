"""Runefoble Dynamic Soundscape & Adaptive Audio Microservice.

Powered by eventsource-py, Redis Streams, and WebAudio stem mixing.
Manages encounter tension scoring, tactical foley sound effects, and -12dB audio ducking.
"""

import contextlib
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from runefoble_platform.aggregate_loading import register_store_unavailable_handlers
from runefoble_platform.event_publish import event_publish_failures
from runefoble_platform.stream_consumer import consumer_statuses
from runefoble_platform.ui_manifest import load_ui_manifest

from soundscape.consumer import start_soundscape_consumers
from soundscape.dependencies import event_bus_provider
from soundscape.event_handlers import register_soundscape_event_handlers
from soundscape.routers.cue import router as cue_router
from soundscape.routers.leitmotif import router as leitmotif_router
from soundscape.routers.stems import router as stems_router
from soundscape.routers.tension import router as tension_router

# Start-up fails when the manifest is missing or invalid. No fallback manifest exists (ADR-0015 4).
UI_MANIFEST = load_ui_manifest(
    Path(__file__).resolve().parent.parent.parent / "ui" / "manifest.json"
)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Bootstrap service lifecycle, event handlers, and the Redis Streams consumer."""
    register_soundscape_event_handlers()
    bus = await event_bus_provider.connect()
    consumers = await start_soundscape_consumers(bus)
    app.state.consumers = {"soundscape": consumers}
    try:
        yield
    finally:
        await consumers.stop()
        await event_bus_provider.close()
        app.state.consumers = {}


app = FastAPI(
    title="Runefoble - Dynamic Soundscape & Adaptive Audio Service",
    version="0.1.0",
    description="Dynamic soundscape, tension scoring, foley cues, and WebAudio ducking microservice.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_store_unavailable_handlers(app)
app.include_router(cue_router)
app.include_router(tension_router)
app.include_router(stems_router)
app.include_router(leitmotif_router)


@app.get("/healthz", tags=["Health"])
@app.get("/health", tags=["Health"])
def health_check(request: Request) -> JSONResponse:
    """Report service health and the status of each supervised stream consumer."""
    statuses = consumer_statuses(getattr(request.app.state, "consumers", {}))
    healthy = all(status == "running" for status in statuses.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "degraded",
            "service": "soundscape",
            "event_publish_failures": event_publish_failures(),
            "consumers": statuses,
        },
    )


@app.get("/ui/manifest", tags=["Microfrontends"])
def get_ui_manifest() -> dict[str, Any]:
    """Advertise vendored microfrontend components for soundscape controls."""
    return UI_MANIFEST


def main() -> None:
    """Run uvicorn server for Soundscape microservice."""
    import uvicorn

    uvicorn.run("soundscape.main:app", host="0.0.0.0", port=8009, reload=True)


if __name__ == "__main__":
    main()
