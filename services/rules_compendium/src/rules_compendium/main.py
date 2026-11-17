"""Runefoble Rules Compendium & Automated CR Encounter Builder Microservice.

Powered by redstring and eventsource-py.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from runefoble_platform.config import EmbeddingEndpointSettings, RulesCompendiumSettings

from rules_compendium.retrieval_factory import build_retrieval_engine
from rules_compendium.routers.encounters import router as encounters_router
from rules_compendium.routers.homebrew import router as homebrew_router
from rules_compendium.routers.rules import router as rules_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build the retrieval engine from settings and index the SRD dataset before serving.

    Start-up fails if the configured embedding provider is missing a setting.
    """
    engine = build_retrieval_engine(RulesCompendiumSettings(), EmbeddingEndpointSettings())
    await engine.initialize_srd_data()
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

    app.include_router(rules_router)
    app.include_router(encounters_router)
    app.include_router(homebrew_router)
    app.include_router(platform_router)
    return app


platform_router = APIRouter()


@platform_router.get("/healthz", tags=["Health"])
@platform_router.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "rules_compendium"}


@platform_router.get("/ui/manifest", tags=["Microfrontends"])
def get_ui_manifest() -> dict[str, Any]:
    """Advertise compendium service manifest."""
    return {
        "service": "rules_compendium",
        "package": "@runefoble/rules-compendium-ui",
        "components": [
            "runefoble-rules-compendium",
            "runefoble-rules-lookup",
            "runefoble-encounter-builder",
            "runefoble-homebrew-creator",
        ],
        "version": "0.1.0",
    }


app = create_app()


def main() -> None:
    """Run uvicorn server for Rules Compendium microservice."""
    import uvicorn

    uvicorn.run("rules_compendium.main:app", host="0.0.0.0", port=8007, reload=True)


if __name__ == "__main__":
    main()
