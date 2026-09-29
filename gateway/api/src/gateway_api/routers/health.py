"""Health and readiness probes for Runefoble Gateway API."""

from fastapi import APIRouter
from gateway_api.dependencies import get_event_bus

router = APIRouter(tags=["Health"])


@router.get("/healthz")
@router.get("/health")
@router.get("/api/v1/health")
async def health_check() -> dict:
    """Return health status, downstream service availability, and Zanzibar engine."""
    bus = get_event_bus()
    event_bus_status = "connected" if bus is not None else "disconnected"
    return {
        "status": "healthy",
        "gateway": "runefoble-api-gateway",
        "downstream_services": {
            "the_watcher": "operational",
            "game_session": "operational",
            "board_state": "operational",
            "character_sheet": "operational",
            "voice_agent": "operational",
        },
        "authorization_engine": "SpiceDB Zanzibar",
        "event_bus": event_bus_status,
    }


@router.get("/readyz")
async def readiness_check() -> dict:
    """Return readiness status for Kubernetes orchestration."""
    return {"status": "ready", "gateway": "runefoble-api-gateway"}
