"""Runefoble Campaign Lore Microservice.

Powered by redstring and eventsource-py.
Extracts knowledge graphs from worldbuilding docs, performs entity alias consolidation,
and provides sub-50ms hybrid RAG retrieval under SpiceDB Zanzibar authorization.
"""

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from campaign_lore.routers.aliases import router as aliases_router
from campaign_lore.routers.documents import router as documents_router
from campaign_lore.routers.handouts import router as handouts_router
from campaign_lore.routers.relics import router as relics_router
from campaign_lore.routers.search import router as search_router

app = FastAPI(
    title="Runefoble - Campaign Lore Service",
    version="0.1.0",
    description="Campaign Lore Knowledge Base & redstring RAG Engine backed by eventsource-py.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
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
            "runefoble-campaign-codex",
            "runefoble-handout-viewer",
            "runefoble-relic-inspector",
        ],
        "version": "0.1.0",
    }


def main() -> None:
    """Run uvicorn server for Campaign Lore microservice."""
    import uvicorn

    uvicorn.run("campaign_lore.main:app", host="0.0.0.0", port=8006, reload=True)


if __name__ == "__main__":
    main()
