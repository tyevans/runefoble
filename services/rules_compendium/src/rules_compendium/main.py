"""Runefoble Rules Compendium & Automated CR Encounter Builder Microservice.

Powered by redstring and eventsource-py.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from runefoble_auth.authz_http import install_authz_error_handlers
from runefoble_auth.readiness import spicedb_probe
from runefoble_platform.aggregate_loading import register_store_unavailable_handlers
from runefoble_platform.config import EmbeddingEndpointSettings, RulesCompendiumSettings
from runefoble_platform.event_publish import event_publish_failures
from runefoble_platform.event_sourcing import get_event_store
from runefoble_platform.readiness import (
    ReadinessGate,
    add_readiness_route,
    event_store_probe,
    set_readiness_gate,
)
from runefoble_platform.ui_manifest import ui_manifest_router

from rules_compendium.projection import rebuild_homebrew_projection
from rules_compendium.retrieval_factory import build_retrieval_engine
from rules_compendium.routers.encounters import router as encounters_router
from rules_compendium.routers.homebrew import router as homebrew_router
from rules_compendium.routers.rules import router as rules_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build the retrieval engine, index the SRD dataset, and replay homebrew events before serving.

    Start-up fails if the configured embedding provider is missing a setting, or if the
    event store cannot be read. The service never serves an empty homebrew index.
    """
    set_readiness_gate(
        app, ReadinessGate({"event_store": event_store_probe(), "spicedb": spicedb_probe()})
    )
    engine = build_retrieval_engine(RulesCompendiumSettings(), EmbeddingEndpointSettings())
    await engine.initialize_srd_data()
    await rebuild_homebrew_projection(engine, get_event_store())
    app.state.retrieval_engine = engine
    yield


def create_app() -> FastAPI:
    """Create a Rules Compendium application instance. Each instance owns its retrieval engine."""
    app = FastAPI(
        title="Runefoble - Rules Compendium Service",
        version="0.1.0",
        description="TTRPG Rules Compendium & Automated CR Encounter Builder Microservice backed by redstring and eventsource-py.",
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
    install_authz_error_handlers(app)
    app.include_router(rules_router)
    app.include_router(encounters_router)
    app.include_router(homebrew_router)
    app.include_router(platform_router)
    app.include_router(
        ui_manifest_router(
            Path(__file__).resolve().parents[2] / "ui" / "manifest.json",
            summary="Advertise compendium service manifest",
        )
    )
    return app


platform_router = APIRouter()


@platform_router.get("/healthz", tags=["Health"])
def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "rules_compendium",
        "event_publish_failures": event_publish_failures(),
    }


add_readiness_route(platform_router, "rules_compendium")


# Build the event store now. A deployed service without a reachable store refuses to start (TASK-0707).
get_event_store()

app = create_app()


def main() -> None:
    """Run uvicorn server for Rules Compendium microservice."""
    import uvicorn

    uvicorn.run("rules_compendium.main:app", host="0.0.0.0", port=8007, reload=True)


if __name__ == "__main__":
    main()
