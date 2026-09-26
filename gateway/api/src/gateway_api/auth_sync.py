"""Gateway API router for Zitadel-SpiceDB Zanzibar relationship synchronization."""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException, status
from gateway_api.auth import get_spicedb_client
from pydantic import BaseModel, Field
from runefoble_auth.sync import ZitadelSpiceDBSyncService

logger = logging.getLogger(__name__)

router = APIRouter()

_sync_service: ZitadelSpiceDBSyncService | None = None


def get_sync_service() -> ZitadelSpiceDBSyncService:
    global _sync_service
    if _sync_service is None:
        _sync_service = ZitadelSpiceDBSyncService(spicedb_client=get_spicedb_client())
    return _sync_service


def set_sync_service(service: ZitadelSpiceDBSyncService | None) -> None:
    global _sync_service
    _sync_service = service


# ---------------------------------------------------------------------------
# Request & Response Models
# ---------------------------------------------------------------------------


class SyncUserRequest(BaseModel):
    user_id: str | None = None
    username: str | None = None
    email: str | None = None
    roles: list[str] = Field(default_factory=list)
    campaign_id: str | None = None
    token: str | None = None


class SyncUserResponse(BaseModel):
    status: str = "synchronized"
    user_id: str
    username: str
    synced_relationships: list[str]


class SyncMembershipRequest(BaseModel):
    campaign_id: str
    user_id: str
    role: Literal["gm", "dungeon_master", "player", "spectator", "owner"] = "player"
    session_id: str | None = None
    action: Literal["grant", "revoke"] = "grant"


class SyncMembershipResponse(BaseModel):
    status: str = "membership_updated"
    campaign_id: str
    user_id: str
    role: str
    action: str
    synced_relationships: list[str]


class SyncCharacterOwnershipRequest(BaseModel):
    character_id: str
    user_id: str
    campaign_id: str | None = None


class SyncCharacterOwnershipResponse(BaseModel):
    status: str = "ownership_bound"
    character_id: str
    user_id: str
    campaign_id: str | None = None
    synced_relationships: list[str]


class SyncTokenBindingRequest(BaseModel):
    token_id: str
    character_id: str | None = None
    campaign_id: str | None = None


class SyncTokenBindingResponse(BaseModel):
    status: str = "token_bound"
    token_id: str
    character_id: str | None = None
    campaign_id: str | None = None
    synced_relationships: list[str]


class SyncHealthResponse(BaseModel):
    status: str
    spicedb_connected: bool
    sync_service: str
    backend: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/user", response_model=SyncUserResponse)
async def sync_user_claims(
    req: SyncUserRequest,
    authorization: str | None = Header(None, alias="Authorization"),
) -> SyncUserResponse:
    """Sync Zitadel user claims into SpiceDB Zanzibar relationship tuples."""
    service = get_sync_service()

    # Extract bearer token if passed in header and not in body
    token_to_use = req.token
    if not token_to_use and authorization and authorization.startswith("Bearer "):
        token_to_use = authorization[7:].strip()

    claims_data: dict[str, Any] = req.model_dump()
    if token_to_use:
        claims_data["token"] = token_to_use

    try:
        synced = await service.sync_user_claims(claims_data, campaign_id=req.campaign_id)
        effective_user_id = req.user_id or "user_from_token"
        effective_username = req.username or "Adventurer"
        return SyncUserResponse(
            status="synchronized",
            user_id=effective_user_id,
            username=effective_username,
            synced_relationships=synced,
        )
    except Exception as exc:
        logger.error("Failed to sync user claims: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User synchronization error: {exc}",
        ) from exc


@router.post("/membership", response_model=SyncMembershipResponse)
async def sync_membership(req: SyncMembershipRequest) -> SyncMembershipResponse:
    """Grant or revoke campaign or session roles (gm, player, spectator) in SpiceDB."""
    service = get_sync_service()
    try:
        synced = await service.sync_membership(
            campaign_id=req.campaign_id,
            user_id=req.user_id,
            role=req.role,
            session_id=req.session_id,
            action=req.action,
        )
        return SyncMembershipResponse(
            status="membership_updated",
            campaign_id=req.campaign_id,
            user_id=req.user_id,
            role=req.role,
            action=req.action,
            synced_relationships=synced,
        )
    except Exception as exc:
        logger.error("Failed to sync membership: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Membership synchronization error: {exc}",
        ) from exc


@router.post("/character-ownership", response_model=SyncCharacterOwnershipResponse)
async def sync_character_ownership(
    req: SyncCharacterOwnershipRequest,
) -> SyncCharacterOwnershipResponse:
    """Bind character aggregate to owning user and parent campaign in SpiceDB."""
    service = get_sync_service()
    try:
        synced = await service.sync_character_ownership(
            character_id=req.character_id,
            user_id=req.user_id,
            campaign_id=req.campaign_id,
        )
        return SyncCharacterOwnershipResponse(
            status="ownership_bound",
            character_id=req.character_id,
            user_id=req.user_id,
            campaign_id=req.campaign_id,
            synced_relationships=synced,
        )
    except Exception as exc:
        logger.error("Failed to sync character ownership: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Character ownership synchronization error: {exc}",
        ) from exc


@router.post("/token-binding", response_model=SyncTokenBindingResponse)
async def sync_token_binding(
    req: SyncTokenBindingRequest,
) -> SyncTokenBindingResponse:
    """Bind board token to character aggregate and campaign grid in SpiceDB."""
    service = get_sync_service()
    try:
        synced = await service.sync_board_token(
            token_id=req.token_id,
            character_id=req.character_id,
            campaign_id=req.campaign_id,
        )
        return SyncTokenBindingResponse(
            status="token_bound",
            token_id=req.token_id,
            character_id=req.character_id,
            campaign_id=req.campaign_id,
            synced_relationships=synced,
        )
    except Exception as exc:
        logger.error("Failed to sync token binding: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token binding synchronization error: {exc}",
        ) from exc


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
        sync_service=str(health.get("sync_service", "operational")),
        backend=str(health.get("backend", "mock")),
    )
