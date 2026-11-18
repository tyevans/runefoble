"""Gateway API router for Zitadel-SpiceDB synchronization health.

Membership, character ownership, and token binding have no public sync routes (TASK-0543).
They are granted through campaign, character, and login frontdoors.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from gateway_api.auth import get_spicedb_client
from pydantic import BaseModel
from runefoble_auth.sync import ZitadelSpiceDBSyncService

logger = logging.getLogger(__name__)

router = APIRouter()

_sync_service: ZitadelSpiceDBSyncService | None = None


def get_sync_service() -> ZitadelSpiceDBSyncService:
    global _sync_service
    current_spicedb = get_spicedb_client()
    if _sync_service is None or _sync_service.spicedb is not current_spicedb:
        _sync_service = ZitadelSpiceDBSyncService(spicedb_client=current_spicedb)
    return _sync_service


def set_sync_service(service: ZitadelSpiceDBSyncService | None) -> None:
    global _sync_service
    _sync_service = service


# ---------------------------------------------------------------------------
# Request & Response Models
# ---------------------------------------------------------------------------


class SyncHealthResponse(BaseModel):
    status: str
    spicedb_connected: bool
    sync_service: str
    backend: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health", response_model=SyncHealthResponse)
async def get_sync_health() -> SyncHealthResponse:
    """Report synchronization state and SpiceDB connectivity."""
    service = get_sync_service()
    health = await service.check_health()
    if not health.get("spicedb_connected", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health,
        )
    return SyncHealthResponse(
        status=health.get("status", "healthy"),
        spicedb_connected=bool(health.get("spicedb_connected", True)),
        sync_service=str(health["sync_service"]),
        backend=str(health.get("backend", "mock")),
    )
