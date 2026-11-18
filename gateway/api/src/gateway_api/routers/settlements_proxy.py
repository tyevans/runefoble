"""Settlement haven, establishment, bulletin, and upgrade routes proxied to game_session (TASK-0592).

The gateway verifies the bearer token, then forwards the request with that same token.
game_session verifies the token again and checks every object permission. The gateway keeps
no settlement state and returns no substitute value. A failed upstream call returns the mapping
in `upstream_errors.py`: 503 when unreachable, 502 on upstream 5xx, upstream 4xx unchanged.

Only the `/api/v1` paths are proxied. Each route keeps its owner path and method.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, Request, status
from gateway_api.auth import CurrentPrincipal
from gateway_api.proxy import forward_json
from runefoble_platform.service_client import path

SERVICE = "game_session"
API = "/api/v1"

router = APIRouter(tags=["Settlements & Establishments"])


def _owner_path(*segments: str) -> str:
    """Quote each path segment for the owner. A segment such as `..` is a client error."""
    try:
        return f"{API}{path(*segments)}"
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc


@router.post("/api/v1/campaigns/{campaign_id}/settlements", status_code=status.HTTP_201_CREATED)
async def found_settlement(
    campaign_id: str, request: Request, user: CurrentPrincipal, body: Annotated[Any, Body()]
) -> Any:
    """Found a settlement haven in a campaign (game_session checks campaign write)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="POST",
        path=_owner_path("campaigns", campaign_id, "settlements"),
        json_body=body,
    )


@router.get("/api/v1/campaigns/{campaign_id}/settlements")
async def list_campaign_settlements(
    campaign_id: str, request: Request, user: CurrentPrincipal
) -> Any:
    """List the settlements of a campaign (game_session checks view)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="GET",
        path=_owner_path("campaigns", campaign_id, "settlements"),
    )


@router.get("/api/v1/campaigns/{campaign_id}/settlements/{settlement_id}")
async def get_campaign_settlement(
    campaign_id: str, settlement_id: str, request: Request, user: CurrentPrincipal
) -> Any:
    """Read one settlement projection (game_session checks view)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="GET",
        path=_owner_path("campaigns", campaign_id, "settlements", settlement_id),
    )


@router.post(
    "/api/v1/settlements/{settlement_id}/establishments", status_code=status.HTTP_201_CREATED
)
async def construct_establishment(
    settlement_id: str, request: Request, user: CurrentPrincipal, body: Annotated[Any, Body()]
) -> Any:
    """Construct an establishment in a settlement district (game_session checks upgrade)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="POST",
        path=_owner_path("settlements", settlement_id, "establishments"),
        json_body=body,
    )


@router.get("/api/v1/settlements/{settlement_id}/establishments")
async def list_settlement_establishments(
    settlement_id: str, request: Request, user: CurrentPrincipal
) -> Any:
    """List the establishments of a settlement (game_session checks view)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="GET",
        path=_owner_path("settlements", settlement_id, "establishments"),
    )


@router.get("/api/v1/establishments/{establishment_id}")
async def get_establishment(establishment_id: str, request: Request, user: CurrentPrincipal) -> Any:
    """Read one establishment (game_session checks view)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="GET",
        path=_owner_path("establishments", establishment_id),
    )


@router.post("/api/v1/settlements/{settlement_id}/upgrade-tier")
async def upgrade_settlement_tier(
    settlement_id: str, request: Request, user: CurrentPrincipal, body: Annotated[Any, Body()]
) -> Any:
    """Upgrade a settlement to a higher civic tier (game_session checks upgrade)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="POST",
        path=_owner_path("settlements", settlement_id, "upgrade-tier"),
        json_body=body,
    )


@router.post("/api/v1/establishments/{establishment_id}/upgrade")
async def upgrade_establishment(
    establishment_id: str, request: Request, user: CurrentPrincipal, body: Annotated[Any, Body()]
) -> Any:
    """Upgrade an establishment tier, amenity, or capacity (game_session checks edit)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="POST",
        path=_owner_path("establishments", establishment_id, "upgrade"),
        json_body=body,
    )


@router.post("/api/v1/settlements/{settlement_id}/bulletin", status_code=status.HTTP_201_CREATED)
async def pin_bulletin_notice(
    settlement_id: str, request: Request, user: CurrentPrincipal, body: Annotated[Any, Body()]
) -> Any:
    """Pin a notice to the settlement bulletin board (game_session checks the board)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="POST",
        path=_owner_path("settlements", settlement_id, "bulletin"),
        json_body=body,
    )


@router.get("/api/v1/settlements/{settlement_id}/bulletin")
async def list_bulletin_notices(
    settlement_id: str, request: Request, user: CurrentPrincipal
) -> Any:
    """List the bulletin notices of a settlement (game_session checks view)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="GET",
        path=_owner_path("settlements", settlement_id, "bulletin"),
    )


@router.delete("/api/v1/settlements/{settlement_id}/bulletin/{notice_id}")
async def remove_bulletin_notice(
    settlement_id: str,
    notice_id: str,
    request: Request,
    user: CurrentPrincipal,
    reason: str = "removed",
) -> Any:
    """Remove or fulfill a bulletin notice (game_session checks the board)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="DELETE",
        path=_owner_path("settlements", settlement_id, "bulletin", notice_id),
        params={"reason": reason},
    )


@router.post("/api/v1/settlements/{settlement_id}/bulletin/{notice_id}/decrypt")
async def decrypt_cipher_notice(
    settlement_id: str,
    notice_id: str,
    request: Request,
    user: CurrentPrincipal,
    body: Annotated[Any, Body()],
) -> Any:
    """Submit a cipher solution for a hidden bulletin notice (game_session checks the board)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="POST",
        path=_owner_path("settlements", settlement_id, "bulletin", notice_id, "decrypt"),
        json_body=body,
    )
