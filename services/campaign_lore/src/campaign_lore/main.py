"""Runefoble Campaign Lore Microservice.

Powered by redstring and eventsource-py.
Extracts knowledge graphs from worldbuilding docs, performs entity alias consolidation,
and provides sub-50ms hybrid RAG retrieval under SpiceDB Zanzibar authorization.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from runefoble_platform.config import LoreBackendSettings, PlatformSettings
from runefoble_platform.event_sourcing import PostgreSQLEventStore, get_event_store

from campaign_lore.codex import CodexCrossReferencer
from campaign_lore.projection import rebuild_lore_projection
from campaign_lore.retrieval_factory import build_retrieval_engine
from campaign_lore.routers.aliases import router as aliases_router
from campaign_lore.routers.atlas import router as atlas_router
from campaign_lore.routers.codex import router as codex_router
from campaign_lore.routers.documents import router as documents_router
from campaign_lore.routers.handouts import router as handouts_router
from campaign_lore.routers.relics import router as relics_router
from campaign_lore.routers.search import router as search_router
from campaign_lore.routers.west_marches import router as west_marches_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build the retrieval engine and replay lore events before serving requests.

    Start-up fails if the configured event store is not available. The service never
    serves from an empty projection while its durable store is down.
    """
    store = get_event_store()
    if PlatformSettings().use_postgres_event_store and not isinstance(store, PostgreSQLEventStore):
        raise RuntimeError(
            "PostgreSQL event store is configured but unreachable; refusing to start "
            "Campaign Lore with an empty projection."
        )
    engine = build_retrieval_engine(LoreBackendSettings())
    await rebuild_lore_projection(engine, store)
    app.state.retrieval_engine = engine
    app.state.codex_referencer = CodexCrossReferencer(engine)
    yield


def create_app() -> FastAPI:
    """Create a Campaign Lore application instance. Each instance owns its projection."""
    app = FastAPI(
        title="Runefoble - Campaign Lore Service",
        version="0.1.0",
        description="Campaign Lore Knowledge Base & redstring RAG Engine backed by eventsource-py.",
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

    app.include_router(documents_router)
    app.include_router(aliases_router)
    app.include_router(search_router)
    app.include_router(handouts_router)
    app.include_router(relics_router)
    app.include_router(atlas_router)
    app.include_router(codex_router)
    app.include_router(west_marches_router)
    _register_routes(app)
    return app


def _register_routes(app: FastAPI) -> None:

    @app.get("/healthz", tags=["Health"])
    @app.get("/health", tags=["Health"])
    def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok", "service": "campaign_lore"}

    @app.get("/ui/manifest", tags=["Microfrontends"])
    def get_ui_manifest() -> dict[str, Any]:
        """Advertise vendored microfrontend components for campaign lore and codex."""
        return {
            "service": "campaign_lore",
            "package": "@runefoble/campaign-lore-ui",
            "components": [
                "runefoble-campaign-atlas",
                "runefoble-campaign-codex",
                "runefoble-handout-viewer",
                "runefoble-relic-inspector",
                "runefoble-west-marches-atlas",
            ],
            "version": "0.1.0",
        }


app = create_app()


def main() -> None:
    """Run uvicorn server for Campaign Lore microservice."""
    import uvicorn

    uvicorn.run("campaign_lore.main:app", host="0.0.0.0", port=8006, reload=True)


if __name__ == "__main__":
    main()
