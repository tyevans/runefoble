"""Downtime, crafting, campfire, tavern and haggling routes proxied to their owners (TASK-0584).

The gateway verifies the bearer token, then forwards the request with that same token.
game_session and character_sheet check every object permission (ADR-0001, ADR-0015).
The gateway holds no stronghold, treasury, boon or recipe state. It has no canned payloads.
A failed upstream call returns the mapping in `upstream_errors.py`.

Owner routes:
- stronghold and campfire: game_session
- tavern games and merchant haggling: game_session
- recipe combine: character_sheet

Pure pass-through routes are rows in `ROUTES` (TASK-0822). The haggling route stays hand-written:
it maps the public body onto another owner route.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from gateway_api.auth import CallerPrincipal
from gateway_api.models import (
    CampfireRestGatewayRequest,
    CombineReagentsGatewayRequest,
    DepositStrongholdGatewayRequest,
    HaggleGatewayRequest,
    StartMinigameGatewayRequest,
    UpgradeStrongholdGatewayRequest,
)
from gateway_api.proxy import forward_json
from gateway_api.proxy_table import ProxyRoute, register_proxy_routes

GAME_SESSION = "game_session"
CHARACTER_SHEET = "character_sheet"

router = APIRouter(tags=["Downtime & Crafting"])

ROUTES = (
    ProxyRoute(
        "GET",
        "/api/v1/campaigns/{campaign_id}/stronghold",
        ("api", "v1", "campaigns", "{campaign_id}", "stronghold"),
        GAME_SESSION,
        name="get_stronghold_gateway",
        doc="Read the campaign stronghold from game_session (requires `view` there).",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/campaigns/{campaign_id}/stronghold/upgrade",
        ("api", "v1", "campaigns", "{campaign_id}", "stronghold", "upgrade"),
        GAME_SESSION,
        name="upgrade_stronghold_gateway",
        doc="Upgrade a stronghold facility in game_session (owner checks `play` or `upgrade`).",
        body="json",
        body_model=UpgradeStrongholdGatewayRequest,
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/campaigns/{campaign_id}/stronghold/deposit",
        ("api", "v1", "campaigns", "{campaign_id}", "stronghold", "deposit"),
        GAME_SESSION,
        name="deposit_stronghold_gateway",
        doc=(
            "Add gold and materials to the campaign stronghold in game_session "
            "(owner checks `stronghold.manage`)."
        ),
        body="json",
        body_model=DepositStrongholdGatewayRequest,
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/sessions/{session_id}/rest/campfire",
        ("api", "v1", "sessions", "{session_id}", "rest", "campfire"),
        GAME_SESSION,
        name="campfire_rest_gateway",
        doc="Run a campfire rest in game_session and return its boons (owner checks `stronghold.manage`).",
        body="json",
        body_model=CampfireRestGatewayRequest,
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/crafting/recipes/combine",
        ("api", "v1", "crafting", "recipes", "combine"),
        CHARACTER_SHEET,
        name="combine_reagents_gateway",
        doc="Combine reagents in character_sheet (owner checks `edit` on the character).",
        body="json",
        body_model=CombineReagentsGatewayRequest,
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/sessions/{session_id}/tavern/games",
        ("api", "v1", "sessions", "{session_id}", "tavern", "games"),
        GAME_SESSION,
        name="start_minigame_gateway",
        doc="Start a tavern minigame in game_session (owner checks session participation).",
        body="json",
        body_model=StartMinigameGatewayRequest,
        principal=True,
    ),
)

register_proxy_routes(router, ROUTES)


@router.post("/api/v1/sessions/{session_id}/merchants/{merchant_id}/haggle")
async def haggle_merchant_gateway(
    session_id: str,
    merchant_id: str,
    req: HaggleGatewayRequest,
    request: Request,
    user: CallerPrincipal,
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
