"""Health and readiness probes for Runefoble Gateway API."""

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from gateway_api.dependencies import get_event_bus, get_upstreams
from runefoble_platform.event_publish import event_publish_failures
from runefoble_platform.service_client import probe_health
from runefoble_platform.stream_consumer import RUNNING, consumer_statuses

router = APIRouter(tags=["Health"])

# Downstream services that /healthz probes, in report order.
DOWNSTREAM_HEALTH_SERVICES = (
    "the_watcher",
    "game_session",
    "board_state",
    "character_sheet",
    "voice_agent",
    "campaign_lore",
)


@router.get("/healthz")
async def health_check(request: Request) -> JSONResponse:
    """Return health status, probed downstream service status, consumers, and Zanzibar engine.

    A downstream failure appears in `downstream_services` and does not fail the liveness check
    (TASK-0674). A failed in-process stream consumer does: the reply is 503 with status
    `degraded`, so the orchestrator restarts the pod (TASK-0923).
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
    consumers = consumer_statuses(getattr(request.app.state, "consumers", {}))
    healthy = all(status == RUNNING for status in consumers.values())
    body = {
        "status": "healthy" if healthy else "degraded",
        "gateway": "runefoble-api-gateway",
        "event_publish_failures": event_publish_failures(),
        "downstream_services": {
            service: status.value
            for service, status in zip(DOWNSTREAM_HEALTH_SERVICES, statuses, strict=True)
        },
        "authorization_engine": "SpiceDB Zanzibar",
        "event_bus": event_bus_status,
        "consumers": consumers,
    }
    return JSONResponse(status_code=200 if healthy else 503, content=body)


@router.get("/readyz")
async def readiness_check() -> dict:
    """Return readiness status for Kubernetes orchestration."""
    return {"status": "ready", "gateway": "runefoble-api-gateway"}
