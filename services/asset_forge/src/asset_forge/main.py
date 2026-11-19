"""Runefoble Procedural Battlemap & Token Asset Forge Microservice.

Powered by eventsource-py and Silo S3.
Synthesizes procedural battlemap tiles, calculates line-of-sight wall segments,
crops transparent circular token portraits, and pushes spatial geometry to board_state.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from runefoble_auth.authz_http import install_authz_error_handlers
from runefoble_platform.aggregate_loading import register_store_unavailable_handlers
from runefoble_platform.engine_ports import EngineUnavailableError, engine_unavailable_handler
from runefoble_platform.event_publish import event_publish_failures
from runefoble_platform.event_sourcing import get_event_store
from runefoble_platform.ui_manifest import load_ui_manifest

from asset_forge.dependencies import event_bus_provider, get_wardrobe_generator
from asset_forge.map_generation_engine import get_map_generator
from asset_forge.routers.assets import router as assets_router
from asset_forge.routers.battlemap import router as battlemap_router
from asset_forge.routers.campaign_records import router as campaign_records_router
from asset_forge.routers.print_forge import router as print_forge_router
from asset_forge.routers.token import router as token_router
from asset_forge.routers.wardrobe import router as wardrobe_router

# Start-up fails when the manifest is missing or invalid. No fallback manifest exists (ADR-0015 4).
UI_MANIFEST = load_ui_manifest(
    Path(__file__).resolve().parent.parent.parent / "ui" / "manifest.json"
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build the configured generators at start-up. A bad generator setting stops the service."""
    get_map_generator()
    get_wardrobe_generator()
    async with event_bus_provider.lifespan(app):
        yield


# Build the event store now. A deployed service without a reachable store refuses to start (TASK-0707).
get_event_store()

app = FastAPI(
    title="Runefoble - Procedural Battlemap & Token Asset Forge Service",
    version="0.1.0",
    description="Procedural Battlemap & Token Asset Forge Microservice backed by Silo S3 and eventsource-py.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
app.add_exception_handler(EngineUnavailableError, engine_unavailable_handler)
register_store_unavailable_handlers(app)


install_authz_error_handlers(app)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assets_router)
app.include_router(battlemap_router)
app.include_router(token_router)
app.include_router(print_forge_router)
app.include_router(wardrobe_router)
app.include_router(campaign_records_router)


@app.get("/healthz", tags=["Health"])
def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "asset_forge",
        "event_publish_failures": event_publish_failures(),
    }


@app.get("/ui/manifest", tags=["Microfrontends"])
def get_ui_manifest() -> dict[str, Any]:
    """Advertise vendored microfrontend components for procedural asset forge."""
    return UI_MANIFEST


def main() -> None:
    """Run uvicorn server for Asset Forge microservice."""
    import uvicorn

    uvicorn.run("asset_forge.main:app", host="0.0.0.0", port=8008, reload=True)


if __name__ == "__main__":
    main()
