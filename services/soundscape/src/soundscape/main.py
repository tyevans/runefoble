"""Runefoble Dynamic Soundscape & Adaptive Audio Microservice.

Powered by eventsource-py, Redis Streams, and WebAudio stem mixing.
Manages encounter tension scoring, tactical foley sound effects, and -12dB audio ducking.
"""

import contextlib
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from soundscape.event_handlers import register_soundscape_event_handlers
from soundscape.routers.cue import router as cue_router
from soundscape.routers.leitmotif import router as leitmotif_router
from soundscape.routers.stems import router as stems_router
from soundscape.routers.tension import router as tension_router


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Bootstrap service lifecycle and wire event handlers."""
    register_soundscape_event_handlers()
    yield


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
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "soundscape"}


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
