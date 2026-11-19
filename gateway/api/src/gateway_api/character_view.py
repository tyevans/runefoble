"""Map character_sheet payloads to the public character contract (TASK-0585).

character_sheet owns character state. The gateway keeps no character state. It translates the
public request body into the owner's create request and the owner's roster view into the
public `CharacterResponse` (snake_case and camelCase fields).

The owner stores `level` and the portrait at creation and validates both (TASK-0905).
The owner does not store a starting HP other than the maximum, the stand-in flag at
creation, or a client-chosen id. A create request that sets one of these
to a value the owner cannot keep returns 422. It is never dropped silently.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
from gateway_api.campaign_titles import campaign_titles
from gateway_api.character_models import CharacterResponse, CreateCharacterRequest
from gateway_api.proxy import forward_json
from runefoble_platform.service_client import owner_routes

CHARACTER_SERVICE = "character_sheet"


async def forward_character_state(
    request: Request,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    params: dict[str, str] | None = None,
) -> CharacterResponse:
    """Forward one character mutation and return the character state the owner answered with."""
    view = await forward_json(
        request,
        service=CHARACTER_SERVICE,
        method=method,
        path=path,
        json_body=body,
        params=params,
    )
    return await respond_with_campaign_title(request, view)


async def respond_with_campaign_title(request: Request, view: dict[str, Any]) -> CharacterResponse:
    """Build the public response and attach the campaign title, read through game_session (G-12).

    Every character reply carries the same title: a list, a read and a mutation alike.
    """
    campaign_id = view.get("campaign_id")
    title = (await campaign_titles(request, {campaign_id}))[campaign_id] if campaign_id else None
    return to_character_response(view, title)


def unsupported_create_fields(req: CreateCharacterRequest) -> list[str]:
    """Name each supplied field that character_sheet cannot store at creation."""
    rejected: list[str] = []
    fields = req.model_fields_set
    if "id" in fields and req.id is not None:
        rejected.append("id")
    if "current_hp" in fields and req.current_hp is not None and req.current_hp != req.max_hp:
        rejected.append("currentHp")
    if req.is_stand_in_active:
        rejected.append("isAiStandIn")
    return rejected


def to_owner_create_payload(req: CreateCharacterRequest) -> dict[str, Any]:
    """Translate the public create body into character_sheet's create request."""
    rejected = unsupported_create_fields(req)
    if rejected:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "unsupported_fields",
                "message": "character_sheet cannot store these fields at creation",
                "fields": rejected,
            },
        )
    return {
        "name": req.name,
        "character_class": req.character_class,
        "subclass": req.subclass,
        "max_hp": req.max_hp,
        "level": req.level,
        "portrait_url": req.portrait_url,
        "armor_class": req.armor_class,
        "speed_ft": req.speed,
        "campaign_id": req.campaign_id,
    }


def to_character_response(view: dict[str, Any], campaign_title: str | None) -> CharacterResponse:
    """Build the public response from character_sheet's roster view."""
    return CharacterResponse(
        id=view["character_id"],
        name=view["name"],
        character_class=view["character_class"],
        subclass=view.get("subclass"),
        level=view["level"],
        current_hp=view["current_hp"],
        max_hp=view["max_hp"],
        armor_class=view["armor_class"],
        speed=view["speed_ft"],
        campaign_id=view.get("campaign_id"),
        campaign_title=campaign_title,
        owner_id=view.get("owner_id") or "",
        portrait_url=view["active_portrait_url"],
        equipment=view["equipment"],
        inventory=view["inventory"],
        conditions=view["conditions"],
        penalties=view["penalties"],
        spell_slots=view["spell_slots"],
        # character_sheet keeps no separate maximum. The current slots are the only figure.
        max_spell_slots=view["spell_slots"],
        prepared_spells=view["prepared_spells"],
        spellbook=view["spellbook"],
        stand_in_guardrails=view["stand_in_guardrails"],
        is_stand_in_active=view["is_stand_in_active"],
        is_stabilized=view["is_stabilized"],
    )


async def campaign_character_names(request: Request, campaign_id: str) -> dict[str, str]:
    """Return {owner id: character name} for the characters the caller sees in one campaign."""
    route = owner_routes.list_characters()
    views = await forward_json(
        request,
        service=CHARACTER_SERVICE,
        method=route.method,
        path=route.path,
        params={"campaignId": campaign_id},
    )
    names: dict[str, str] = {}
    for view in views:
        names.setdefault(view.get("owner_id") or "", view["name"])
    return names
