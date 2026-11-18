"""Downtime, crafting, campfire, tavern and haggling routes proxied to their owners (TASK-0584).

The gateway verifies the bearer token, then forwards the request with that same token.
game_session and character_sheet check every object permission (ADR-0001, ADR-0015).
The gateway holds no stronghold, treasury, boon or recipe state. It has no canned payloads.
A failed upstream call returns the mapping in `upstream_errors.py`.

Owner routes:
- stronghold and campfire: game_session
- tavern games and merchant haggling: game_session
- recipe combine: character_sheet
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from gateway_api.auth import CurrentPrincipal
from gateway_api.models import (
    CampfireRestGatewayRequest,
    CombineReagentsGatewayRequest,
    DepositStrongholdGatewayRequest,
    HaggleGatewayRequest,
    StartMinigameGatewayRequest,
    UpgradeStrongholdGatewayRequest,
)
from gateway_api.proxy import forward_json
from runefoble_platform.service_client import path

GAME_SESSION = "game_session"
CHARACTER_SHEET = "character_sheet"

router = APIRouter(tags=["Downtime & Crafting"])


@router.get("/api/v1/campaigns/{campaign_id}/stronghold")
async def get_stronghold_gateway(campaign_id: str, request: Request, user: CurrentPrincipal) -> Any:
    """Read the campaign stronghold from game_session (requires `view` there)."""
    return await forward_json(
        request,
        service=GAME_SESSION,
        method="GET",
        path=path("api", "v1", "campaigns", campaign_id, "stronghold"),
    )


@router.post("/api/v1/campaigns/{campaign_id}/stronghold/upgrade")
async def upgrade_stronghold_gateway(
    campaign_id: str,
    req: UpgradeStrongholdGatewayRequest,
    request: Request,
    user: CurrentPrincipal,
) -> Any:
    """Upgrade a stronghold facility in game_session (owner checks `play` or `upgrade`)."""
    return await forward_json(
        request,
        service=GAME_SESSION,
        method="POST",
        path=path("api", "v1", "campaigns", campaign_id, "stronghold", "upgrade"),
        json_body=req.model_dump(mode="json"),
    )


@router.post("/api/v1/campaigns/{campaign_id}/stronghold/deposit")
async def deposit_stronghold_gateway(
    campaign_id: str,
    req: DepositStrongholdGatewayRequest,
    request: Request,
    user: CurrentPrincipal,
) -> Any:
    """Add gold and materials to the campaign stronghold in game_session (owner checks `stronghold.manage`)."""
    return await forward_json(
        request,
        service=GAME_SESSION,
        method="POST",
        path=path("api", "v1", "campaigns", campaign_id, "stronghold", "deposit"),
        json_body=req.model_dump(mode="json"),
    )


@router.post("/api/v1/sessions/{session_id}/rest/campfire")
async def campfire_rest_gateway(
    session_id: str,
    req: CampfireRestGatewayRequest,
    request: Request,
    user: CurrentPrincipal,
) -> Any:
    """Run a campfire rest in game_session and return its boons (owner checks `stronghold.manage`)."""
    return await forward_json(
        request,
        service=GAME_SESSION,
        method="POST",
        path=path("api", "v1", "sessions", session_id, "rest", "campfire"),
        json_body=req.model_dump(mode="json"),
    )


@router.post("/api/v1/crafting/recipes/combine")
async def combine_reagents_gateway(
    req: CombineReagentsGatewayRequest,
    request: Request,
    user: CurrentPrincipal,
) -> Any:
    """Combine reagents in character_sheet (owner checks `edit` on the character)."""
    return await forward_json(
        request,
        service=CHARACTER_SHEET,
        method="POST",
        path="/api/v1/crafting/recipes/combine",
        json_body=req.model_dump(mode="json"),
    )


@router.post("/api/v1/sessions/{session_id}/tavern/games")
async def start_minigame_gateway(
    session_id: str,
    req: StartMinigameGatewayRequest,
    request: Request,
    user: CurrentPrincipal,
) -> Any:
    """Start a tavern minigame in game_session (owner checks session participation)."""
    return await forward_json(
        request,
        service=GAME_SESSION,
        method="POST",
        path=path("api", "v1", "sessions", session_id, "tavern", "games"),
        json_body=req.model_dump(mode="json"),
    )


@router.post("/api/v1/sessions/{session_id}/merchants/{merchant_id}/haggle")
async def haggle_merchant_gateway(
    session_id: str,
    merchant_id: str,
    req: HaggleGatewayRequest,
    request: Request,
    user: CurrentPrincipal,
) -> Any:
    """Start a merchant negotiation in game_session.

    game_session has no route keyed by session and merchant. This maps to
    `POST /api/v1/haggling/start` and passes the merchant and session in the body.
    """
    return await forward_json(
        request,
        service=GAME_SESSION,
        method="POST",
        path="/api/v1/haggling/start",
        json_body={
            "character_id": req.character_id,
            "campaign_id": req.campaign_id,
            "establishment_id": req.establishment_id,
            "session_id": session_id,
            "merchant_id": merchant_id,
            "item_id": req.item_id,
            "item_name": req.item_name,
            "base_price": req.base_price,
            "offered_price": req.offered_price,
            "charisma_modifier": req.charisma_modifier,
            "dialogue": req.dialogue,
            "temperament": req.temperament,
        },
    )
