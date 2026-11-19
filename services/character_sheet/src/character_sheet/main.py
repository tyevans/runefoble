"""Character Sheet Microservice - Powered by eventsource-py.

Manages player and NPC character sheets, hit points, inventories,
equipment, and status conditions (such as DM penalties for missed sessions).
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from pathlib import Path

from character_sheet.audience_status import start_audience_status_consumers
from character_sheet.crafting_router import router as crafting_router
from character_sheet.dependencies import (
    STREAM_CHARACTER,
    event_bus_provider,
    get_event_bus,
    get_repository,
    repo,
    set_event_bus,
)
from character_sheet.router import router
from character_sheet.wardrobe_router import router as wardrobe_router
from fastapi import FastAPI, Request
from runefoble_auth.authz_http import install_authz_error_handlers
from runefoble_auth.readiness import spicedb_probe
from runefoble_platform.aggregate_loading import register_store_unavailable_handlers
from runefoble_platform.domain_errors_http import install_domain_error_handlers
from runefoble_platform.event_publish import event_publish_failures
from runefoble_platform.event_sourcing import event_store_kind, get_event_store
from runefoble_platform.readiness import (
    ReadinessGate,
    add_readiness_route,
    event_store_probe,
    redis_probe,
    set_readiness_gate,
)
from runefoble_platform.stream_consumer import consumer_statuses
from runefoble_platform.ui_manifest import ui_manifest_router

# Build the event store now. A deployed service without a reachable store refuses to start (TASK-0707).
get_event_store()


@contextlib.asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Connect the Redis bus, start the audience status consumer, and stop both at shutdown."""
    readiness = {
        "event_store": event_store_probe(),
        "spicedb": spicedb_probe(),
        "redis": redis_probe(get_event_bus),
    }
    set_readiness_gate(app, ReadinessGate(readiness))
    bus = await event_bus_provider.connect()
    consumers = await start_audience_status_consumers(bus)
    app.state.consumers = {"character_sheet": consumers}
    try:
        yield
    finally:
        await consumers.stop()
        await event_bus_provider.close()
        app.state.consumers = {}


app = FastAPI(
    title="Runefoble - Character Sheet Service",
    version="0.1.0",
    description="Character Stats, HP Tracking, Inventory, Equipment, and DM Penalties backed by eventsource-py.",
    lifespan=_lifespan,
)

app.include_router(router)
app.include_router(crafting_router)
app.include_router(wardrobe_router)
app.include_router(
    ui_manifest_router(
        Path(__file__).resolve().parents[2] / "ui" / "manifest.json",
        summary="Advertise vendored microfrontend components for character sheet",
    )
)
register_store_unavailable_handlers(app)
install_authz_error_handlers(app)
install_domain_error_handlers(app)


@app.get("/healthz")
async def health_check(request: Request):
    return {
        "status": "ok",
        "service": "character_sheet",
        "event_store": event_store_kind(),
        "event_publish_failures": event_publish_failures(),
        "consumers": consumer_statuses(getattr(request.app.state, "consumers", {})),
    }


add_readiness_route(app, "character_sheet")


def main():
    import uvicorn

    uvicorn.run("character_sheet.main:app", host="0.0.0.0", port=8003, reload=True)


if __name__ == "__main__":
    main()

__all__ = [
    "STREAM_CHARACTER",
    "app",
    "get_event_bus",
    "get_repository",
    "main",
    "repo",
    "router",
    "set_event_bus",
]
