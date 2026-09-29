from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from gateway_api.auth import get_current_user, get_spicedb_client, require_zanzibar_permission
from gateway_api.character_models import (
    AssignCampaignRequest,
    CharacterResponse,
    CreateCharacterRequest,
)
from gateway_api.character_store import character_store
from gateway_api.routers.character_subresources import router as subresources_router
from runefoble_auth.zitadel import AuthenticatedUser

router = APIRouter(tags=["Characters"])
router.include_router(subresources_router)


@router.get("/api/v1/characters", response_model=list[CharacterResponse])
async def list_characters(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    campaign_id: str | None = Query(None, alias="campaignId"),
) -> list[CharacterResponse]:
    """List characters viewable by current user under SpiceDB Zanzibar rules."""
    all_chars = character_store.list_characters()
    client = get_spicedb_client()
    allowed = []

    for char in all_chars:
        if campaign_id and char.campaign_id != campaign_id:
            continue

        if char.owner_id == user.user_id:
            allowed.append(char)
            continue

        has_view = await client.check_permission("character", char.id, "view", "user", user.user_id)
        if has_view:
            allowed.append(char)

    return [c.to_response() for c in allowed]


@router.post(
    "/api/v1/characters",
    response_model=CharacterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_character(
    req: CreateCharacterRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> CharacterResponse:
    """Create a new character and assign ownership to caller in SpiceDB."""
    char = character_store.create_from_request(req, owner_id=user.user_id)

    client = get_spicedb_client()
    await client.write_relationship("character", char.id, "owner", "user", user.user_id)

    if char.campaign_id:
        await client.write_relationship(
            "character", char.id, "campaign", "campaign", char.campaign_id
        )

    return char.to_response()


@router.get(
    "/api/v1/characters/{character_id}",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("view", "character", "character_id"))],
)
async def get_character(
    character_id: str,
) -> CharacterResponse:
    """Retrieve full character sheet with dual-case serialization (requires 'view')."""
    char = character_store.get_character(character_id)
    if not char:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")
    return char.to_response()


@router.patch(
    "/api/v1/characters/{character_id}/campaign",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def assign_campaign(
    character_id: str,
    req: AssignCampaignRequest,
) -> CharacterResponse:
    """Assign or unassign character to campaign and synchronize SpiceDB (requires 'edit')."""
    char = character_store.get_character(character_id)
    if not char:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")

    client = get_spicedb_client()
    old_campaign = char.campaign_id

    if old_campaign and old_campaign != req.campaign_id:
        await client.delete_relationship(
            "character", character_id, "campaign", "campaign", old_campaign
        )

    if req.campaign_id:
        await client.write_relationship(
            "character", character_id, "campaign", "campaign", req.campaign_id
        )

    updated = character_store.assign_campaign(character_id, req.campaign_id)
    return (updated or char).to_response()


@router.delete(
    "/api/v1/characters/{character_id}",
    dependencies=[Depends(require_zanzibar_permission("owner", "character", "character_id"))],
)
async def delete_character(
    character_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Delete owned character and remove SpiceDB relationships (requires 'owner')."""
    char = character_store.get_character(character_id)
    if not char:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")

    client = get_spicedb_client()
    await client.delete_relationship("character", character_id, "owner", "user", user.user_id)
    if char.campaign_id:
        await client.delete_relationship(
            "character", character_id, "campaign", "campaign", char.campaign_id
        )

    character_store.delete_character(character_id)
    return {"status": "deleted", "character_id": character_id}
