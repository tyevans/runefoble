"""Runefoble Dynamic Soundscape & Adaptive Audio Microservice.

Powered by eventsource-py, Redis Streams, and WebAudio stem mixing.
Manages encounter tension scoring, tactical foley sound effects, and -12dB audio ducking.
"""

import contextlib
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from runefoble_auth.authz_http import install_authz_error_handlers
from runefoble_auth.readiness import spicedb_probe
from runefoble_platform.aggregate_loading import register_store_unavailable_handlers
from runefoble_platform.event_publish import event_publish_failures
from runefoble_platform.event_sourcing import get_event_store
from runefoble_platform.readiness import (
    ReadinessGate,
    add_readiness_route,
    event_store_probe,
    redis_probe,
    set_readiness_gate,
)
from runefoble_platform.stream_consumer import consumer_statuses
from runefoble_platform.ui_manifest import ui_manifest_router

from soundscape.consumer import start_soundscape_consumers
from soundscape.dependencies import event_bus_provider, get_event_bus
from soundscape.routers.cue import router as cue_router
from soundscape.routers.leitmotif import router as leitmotif_router
from soundscape.routers.stems import router as stems_router
from soundscape.routers.tension import router as tension_router


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Bootstrap the Redis Streams bus and the soundscape consumer."""
    readiness = {
        "event_store": event_store_probe(),
        "spicedb": spicedb_probe(),
        "redis": redis_probe(get_event_bus),
    }
    set_readiness_gate(app, ReadinessGate(readiness))
    bus = await event_bus_provider.connect()
    consumers = await start_soundscape_consumers(bus)
    app.state.consumers = {"soundscape": consumers}
    try:
        yield
    finally:
        await consumers.stop()
        await event_bus_provider.close()
        app.state.consumers = {}


# Build the event store now. A deployed service without a reachable store refuses to start (TASK-0707).
get_event_store()

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


install_authz_error_handlers(app)

register_store_unavailable_handlers(app)
app.include_router(cue_router)
app.include_router(tension_router)
app.include_router(stems_router)
app.include_router(leitmotif_router)
app.include_router(
    ui_manifest_router(
        Path(__file__).resolve().parents[2] / "ui" / "manifest.json",
        summary="Advertise vendored microfrontend components for soundscape controls",
    )
)


@app.get("/healthz", tags=["Health"])
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


add_readiness_route(app, "soundscape")


def main() -> None:
    """Run uvicorn server for Soundscape microservice."""
    import uvicorn

    uvicorn.run("soundscape.main:app", host="0.0.0.0", port=8009, reload=True)


if __name__ == "__main__":
    main()
