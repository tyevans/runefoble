"""Health and readiness probes for Runefoble Gateway API."""

import asyncio

from fastapi import APIRouter, Request
from gateway_api.dependencies import get_event_bus, get_upstreams
from runefoble_platform.event_publish import event_publish_failures
from runefoble_platform.service_client import probe_health

router = APIRouter(tags=["Health"])

# Downstream services that /healthz probes, in report order.
DOWNSTREAM_HEALTH_SERVICES = (
    "the_watcher",
    "game_session",
    "board_state",
    "character_sheet",
    "voice_agent",
)


@router.get("/healthz")
@router.get("/health")
@router.get("/api/v1/health")
async def health_check(request: Request) -> dict:
    """Return health status, probed downstream service status, and Zanzibar engine.

    The top-level status stays `healthy` while this process runs. A downstream failure
    appears in `downstream_services` and does not fail the liveness check (TASK-0674).
    """
    upstreams = get_upstreams(request)
    bus = get_event_bus()
    event_bus_status = "connected" if bus is not None else "disconnected"
    statuses = await asyncio.gather(
        *(
            probe_health(upstreams.find(service), timeout_s=upstreams.health_probe_timeout_s)
            for service in DOWNSTREAM_HEALTH_SERVICES
        )
    )
    return {
        "status": "healthy",
        "gateway": "runefoble-api-gateway",
        "event_publish_failures": event_publish_failures(),
        "downstream_services": {
            service: status.value
            for service, status in zip(DOWNSTREAM_HEALTH_SERVICES, statuses, strict=True)
        },
        "authorization_engine": "SpiceDB Zanzibar",
        "event_bus": event_bus_status,
    }


@router.get("/readyz")
async def readiness_check() -> dict:
    """Return readiness status for Kubernetes orchestration."""
    return {"status": "ready", "gateway": "runefoble-api-gateway"}
