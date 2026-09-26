"""Runefoble Campaign Analytics & Chronicle Archive Microservice.

Powered by eventsource-py, Redis Streams, and PostgreSQL.
Projects combat telemetry, tactical damage heatmaps, party MVP turn statistics,
and interactive campaign milestone timelines from distributed domain events.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus

from campaign_analytics.dependencies import (
    get_storage,
    get_worker,
    platform_settings,
    set_event_bus,
    set_storage,
    set_worker,
)
from campaign_analytics.routers import heatmap_router, mvp_router, timeline_router
from campaign_analytics.storage import CampaignAnalyticsStorage
from campaign_analytics.worker import CampaignAnalyticsWorker


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle."""
    # Initialize storage
    storage = await CampaignAnalyticsStorage.create(platform_settings)
    set_storage(storage)

    # Initialize worker if Redis is reachable
    worker: CampaignAnalyticsWorker | None = None
    if platform_settings.redis_url:
        try:
            bus = RedisStreamsEventBus(redis_url=platform_settings.redis_url)
            set_event_bus(bus)
            cg = RedisConsumerGroup(client=bus.client)
            worker = CampaignAnalyticsWorker(
                storage=storage,
                consumer_group=cg,
            )
            set_worker(worker)
            await worker.start()
        except Exception:
            pass

    yield

    if worker:
        await worker.stop()


app = FastAPI(
    title="Runefoble - Campaign Analytics & Chronicle Archive Service",
    version="0.1.0",
    description="Campaign analytics, tactical heatmaps, MVP statistics, and chronicle archive microservice.",
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

app.include_router(heatmap_router)
app.include_router(mvp_router)
app.include_router(timeline_router)


@app.get("/healthz", tags=["Health"])
@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "campaign-analytics"}


@app.get("/metrics", tags=["Observability"])
def get_metrics() -> dict[str, Any]:
    """Prometheus-compatible telemetry metrics."""
    storage = get_storage()
    worker = get_worker()
    return {
        "service": "campaign-analytics",
        "spatial_records_count": len(storage.spatial_records),
        "combatants_count": len(storage.combatants),
        "milestones_count": len(storage.milestones),
        "events_processed": worker.processed_count if worker else 0,
    }


@app.get("/ui/manifest", tags=["Microfrontends"])
def get_ui_manifest() -> dict[str, Any]:
    """Advertise vendored microfrontend components for campaign telemetry and timeline."""
    return {
        "service": "campaign-analytics",
        "package": "@runefoble/campaign-analytics-ui",
        "components": [
            "runefoble-campaign-telemetry",
            "runefoble-chronicle-timeline",
            "runefoble-combat-heatmap",
        ],
        "version": "0.1.0",
    }


def main() -> None:
    """Run uvicorn server for Campaign Analytics microservice."""
    import uvicorn

    uvicorn.run("campaign_analytics.main:app", host="0.0.0.0", port=8011, reload=True)


if __name__ == "__main__":
    main()
