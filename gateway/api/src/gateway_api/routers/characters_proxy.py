"""Character core routes proxied to character_sheet, which owns character state (TASK-0585).

The gateway verifies the bearer token, then forwards the request with that same token.
character_sheet checks every object permission (ADR-0007, ADR-0011, ADR-0015). The gateway
writes no SpiceDB tuple and keeps no character state. A failed upstream call returns the
mapping in `upstream_errors.py`: 503 when unreachable, 502 on upstream 5xx, upstream 4xx unchanged.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request, status
from gateway_api.auth import CallerPrincipal
from gateway_api.campaign_titles import campaign_titles
from gateway_api.character_models import (
    AssignCampaignRequest,
    CharacterResponse,
    CreateCharacterRequest,
)
from gateway_api.character_view import (
    CHARACTER_SERVICE,
    CHARACTERS_PATH,
    respond_with_campaign_title,
    to_character_response,
    to_owner_create_payload,
)
from gateway_api.proxy import forward_json
from gateway_api.routers.characters_spells_guardrails_proxy import (
    router as spells_guardrails_router,
)
from gateway_api.routers.characters_subresources_proxy import router as subresources_router

router = APIRouter(tags=["Characters"])
router.include_router(subresources_router)
router.include_router(spells_guardrails_router)


@router.get("/api/v1/characters", response_model=list[CharacterResponse])
async def list_characters(
    request: Request,
    user: CallerPrincipal,
    campaign_id: Annotated[str | None, Query(alias="campaignId")] = None,
) -> list[CharacterResponse]:
    """List the characters the caller may view (character_sheet)."""
    params = {"campaignId": campaign_id} if campaign_id else None
    views = await forward_json(
        request, service=CHARACTER_SERVICE, method="GET", path=CHARACTERS_PATH, params=params
    )
    titles = await campaign_titles(
        request, {v["campaign_id"] for v in views if v.get("campaign_id")}
    )
    return [to_character_response(v, titles.get(v.get("campaign_id") or "")) for v in views]


@router.post(
    "/api/v1/characters",
    response_model=CharacterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_character(
    req: CreateCharacterRequest, request: Request, user: CallerPrincipal
) -> CharacterResponse:
    """Create a character. character_sheet records the caller as owner (token subject)."""
    view = await forward_json(
        request,
        service=CHARACTER_SERVICE,
        method="POST",
        path=CHARACTERS_PATH,
        json_body=to_owner_create_payload(req),
    )
    return await respond_with_campaign_title(request, view)


@router.get("/api/v1/characters/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: str, request: Request, user: CallerPrincipal
) -> CharacterResponse:
    """Read one character. character_sheet checks `view`."""
    view = await forward_json(
        request, service=CHARACTER_SERVICE, method="GET", path=f"{CHARACTERS_PATH}/{character_id}"
    )
    return await respond_with_campaign_title(request, view)


@router.patch("/api/v1/characters/{character_id}/campaign", response_model=CharacterResponse)
async def assign_campaign(
    character_id: str,
    req: AssignCampaignRequest,
    request: Request,
    user: CallerPrincipal,
) -> CharacterResponse:
    """Assign or unassign the campaign. character_sheet checks `edit` and writes the tuple."""
    view = await forward_json(
        request,
        service=CHARACTER_SERVICE,
        method="PATCH",
        path=f"{CHARACTERS_PATH}/{character_id}/campaign",
        json_body={"campaign_id": req.campaign_id},
    )
    return await respond_with_campaign_title(request, view)
