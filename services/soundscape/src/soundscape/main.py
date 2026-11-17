"""Runefoble Dynamic Soundscape & Adaptive Audio Microservice.

Powered by eventsource-py, Redis Streams, and WebAudio stem mixing.
Manages encounter tension scoring, tactical foley sound effects, and -12dB audio ducking.
"""

import contextlib
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from runefoble_platform.event_publish import event_publish_failures
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.stream_consumer import consumer_statuses

from soundscape.consumer import start_soundscape_consumers
from soundscape.dependencies import settings
from soundscape.event_handlers import register_soundscape_event_handlers
from soundscape.routers.cue import router as cue_router
from soundscape.routers.leitmotif import router as leitmotif_router
from soundscape.routers.stems import router as stems_router
from soundscape.routers.tension import router as tension_router


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Bootstrap service lifecycle, event handlers, and the Redis Streams consumer."""
    register_soundscape_event_handlers()
    bus = RedisStreamsEventBus(redis_url=settings.redis_url)
    consumers = await start_soundscape_consumers(bus)
    app.state.consumers = {"soundscape": consumers}
    try:
        yield
    finally:
        await consumers.stop()
        await bus.close()
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
    manifest_path = Path(__file__).resolve().parent.parent.parent / "ui" / "manifest.json"
    if manifest_path.is_file():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "service": "soundscape",
        "package": "@runefoble/soundscape-ui",
        "components": [
            "runefoble-soundscape-controls",
            "runefoble-leitmotif-config",
        ],
        "tags": [
            "runefoble-soundscape-controls",
            "runefoble-leitmotif-config",
        ],
        "styles": [
            "./src/runefoble-soundscape-controls.styles.ts",
            "./src/runefoble-leitmotif-config.styles.ts",
        ],
        "scripts": ["./src/index.ts"],
        "version": "0.1.0",
    }


def main() -> None:
    """Run uvicorn server for Soundscape microservice."""
    import uvicorn

    uvicorn.run("soundscape.main:app", host="0.0.0.0", port=8009, reload=True)


if __name__ == "__main__":
    main()
