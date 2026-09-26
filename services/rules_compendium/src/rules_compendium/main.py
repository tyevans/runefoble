"""Runefoble Rules Compendium & Automated CR Encounter Builder Microservice.

Powered by redstring and eventsource-py.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rules_compendium.dependencies import get_retrieval_engine
from rules_compendium.routers.encounters import router as encounters_router
from rules_compendium.routers.homebrew import router as homebrew_router
from rules_compendium.routers.rules import router as rules_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize SRD rules dataset into redstring index on startup."""
    engine = get_retrieval_engine()
    await engine.initialize_srd_data()
    yield


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


@app.get("/healthz", tags=["Health"])
@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "rules_compendium"}


@app.get("/ui/manifest", tags=["Microfrontends"])
def get_ui_manifest() -> dict[str, Any]:
    """Advertise compendium service manifest."""
    return {
        "service": "rules_compendium",
        "package": "@runefoble/rules-compendium-ui",
        "components": ["runefoble-rules-lookup", "runefoble-encounter-builder"],
        "version": "0.1.0",
    }


def main() -> None:
    """Run uvicorn server for Rules Compendium microservice."""
    import uvicorn

    uvicorn.run("rules_compendium.main:app", host="0.0.0.0", port=8007, reload=True)


if __name__ == "__main__":
    main()
