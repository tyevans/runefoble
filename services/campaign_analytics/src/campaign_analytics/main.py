"""Runefoble Campaign Analytics & Chronicle Archive Microservice.

Powered by eventsource-py, Redis Streams, and PostgreSQL.
Projects combat telemetry, tactical damage heatmaps, party MVP turn statistics,
and interactive campaign milestone timelines from distributed domain events.

`create_app` is the composition root. It takes explicit settings and an event bus provider.
The module-level `app` is built from environment settings for the process entrypoint.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from eventsource.application.aggregates.repository import AggregateRepository
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from runefoble_auth.authz_http import install_authz_error_handlers
from runefoble_auth.wiring import verifier_from_settings
from runefoble_platform.config import PlatformSettings
from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_publish import event_publish_failures
from runefoble_platform.event_sourcing import create_aggregate_repository
from runefoble_platform.stream_consumer import consumer_statuses
from runefoble_platform.ui_manifest import load_ui_manifest
from sqlalchemy.exc import SQLAlchemyError

from campaign_analytics.aggregate import CampaignChronicleAggregate
from campaign_analytics.dependencies import (
    get_storage,
    get_worker,
    set_storage,
    set_worker,
)
from campaign_analytics.routers import heatmap_router, mvp_router, timeline_router
from campaign_analytics.storage import (
    CampaignAnalyticsStorage,
    StorageUnavailableError,
    require_postgresql,
)
from campaign_analytics.worker import CampaignAnalyticsWorker

# Start-up fails when the manifest is missing or invalid. No fallback manifest exists (ADR-0015 4).
UI_MANIFEST = load_ui_manifest(
    Path(__file__).resolve().parent.parent.parent / "ui" / "manifest.json"
)

system_router = APIRouter()


async def store_unavailable(_request: Request, _exc: Exception) -> JSONResponse:
    """Answer 503 when the read models cannot be reached. Never answer with empty data."""
    return JSONResponse(
        status_code=503,
        content={"detail": "Campaign analytics store is unavailable"},
    )


@system_router.get("/healthz", tags=["Health"])
def health_check(request: Request) -> JSONResponse:
    """Report service health and the status of each supervised stream consumer."""
    statuses = consumer_statuses(getattr(request.app.state, "consumers", {}))
    healthy = all(status == "running" for status in statuses.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "degraded",
            "service": "campaign-analytics",
            "consumers": statuses,
            "event_publish_failures": event_publish_failures(),
        },
    )


@system_router.get("/metrics", tags=["Observability"])
async def get_metrics() -> dict[str, Any]:
    """Prometheus-compatible telemetry metrics."""
    storage = get_storage()
    worker = get_worker()
    return {
        "service": "campaign-analytics",
        **(await storage.counts()),
        "events_processed": worker.processed_count if worker else 0,
    }


@system_router.get("/ui/manifest", tags=["Microfrontends"])
def get_ui_manifest() -> dict[str, Any]:
    """Advertise vendored microfrontend components for campaign telemetry and timeline."""
    return UI_MANIFEST


def create_app(settings: PlatformSettings, event_bus: EventBusProvider) -> FastAPI:
    """Build the Campaign Analytics app from explicit settings and an event bus provider.

    Raises StorageConfigurationError when the configured database is not PostgreSQL. The
    reachability of PostgreSQL and Redis is checked by the lifespan when the app starts.
    """
    require_postgresql(settings)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Connect PostgreSQL, resume the analytics consumers, and stop them on shutdown.

        Any failure while starting raises, so the service does not run without its store.
        """
        storage = await CampaignAnalyticsStorage.create(settings)
        try:
            bus = await event_bus.connect()
            chronicle: AggregateRepository[CampaignChronicleAggregate] = (
                create_aggregate_repository(CampaignChronicleAggregate)
            )
            worker = CampaignAnalyticsWorker(
                storage=storage,
                consumer_group=RedisConsumerGroup(client=await bus.get_client()),
                chronicle=chronicle,
            )
            set_storage(storage)
            set_worker(worker)
            await worker.start()
        except BaseException:
            set_storage(None)
            set_worker(None)
            await event_bus.close()
            await storage.dispose()
            raise

        app.state.consumers = {"analytics": worker.consumers}
        try:
            yield
        finally:
            await worker.stop()
            await event_bus.close()
            await storage.dispose()
            app.state.consumers = {}
            set_storage(None)
            set_worker(None)

    app = FastAPI(
        title="Runefoble - Campaign Analytics & Chronicle Archive Service",
        version="0.1.0",
        description="Campaign analytics, tactical heatmaps, MVP statistics, and chronicle archive microservice.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.state.zitadel_verifier = verifier_from_settings(settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for store_error in (SQLAlchemyError, OSError, StorageUnavailableError):
        app.add_exception_handler(store_error, store_unavailable)
    install_authz_error_handlers(app)

    app.include_router(heatmap_router)
    app.include_router(mvp_router)
    app.include_router(timeline_router)
    app.include_router(system_router)
    return app


def create_app_from_environment() -> FastAPI:
    """Build the app with settings read from the environment at the time of the call."""
    settings = PlatformSettings()
    return create_app(settings, EventBusProvider(settings))


app = create_app_from_environment()


def main() -> None:
    """Run uvicorn server for Campaign Analytics microservice."""
    import uvicorn

    uvicorn.run("campaign_analytics.main:app", host="0.0.0.0", port=8011, reload=True)


if __name__ == "__main__":
    main()
