"""Character management and Zanzibar authorization router for Gateway API."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from gateway_api.auth import get_current_user, get_spicedb_client, require_zanzibar_permission
from gateway_api.character_models import (
    AssignCampaignRequest,
    CharacterResponse,
    CreateCharacterRequest,
)
from gateway_api.character_store import character_store
from runefoble_auth.zitadel import AuthenticatedUser

router = APIRouter(tags=["Characters"])


@router.get("/api/v1/characters", response_model=list[CharacterResponse])
async def list_characters(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    owned_only: bool = Query(default=False, description="Filter strictly to owned characters"),
) -> list[CharacterResponse]:
    """List characters where authenticated user has view or owner relation in SpiceDB."""
    chars = await character_store.list_characters_for_user(
        user.user_id, get_spicedb_client(), owned_only=owned_only
    )
    return [c.to_response() for c in chars]


@router.post(
    "/api/v1/characters",
    response_model=CharacterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_character(
    req: CreateCharacterRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> CharacterResponse:
    """Create a new character and write SpiceDB owner relationship tuple."""
    char = character_store.create_from_request(req, user.user_id)
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
async def get_character(character_id: str) -> CharacterResponse:
    """Fetch character details (requires Zanzibar 'view' permission)."""
    char = character_store.get_character(character_id)
    if not char:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")
    return char.to_response()


@router.patch(
    "/api/v1/characters/{character_id}/campaign",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def assign_character_campaign(
    character_id: str,
    req: AssignCampaignRequest,
) -> CharacterResponse:
    """Assign or unassign character to a campaign (requires Zanzibar 'edit' permission)."""
    char = character_store.get_character(character_id)
    if not char:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")

    client = get_spicedb_client()
    old_campaign_id = char.campaign_id

    # If removing or changing campaign, delete old relationship
    if old_campaign_id and old_campaign_id != req.campaign_id:
        await client.delete_relationship(
            "character", character_id, "campaign", "campaign", old_campaign_id
        )

    # If assigning new campaign, write relationship
    if req.campaign_id and req.campaign_id != old_campaign_id:
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
    # Delete owner relationship
    await client.delete_relationship("character", character_id, "owner", "user", user.user_id)
    # Delete campaign relationship if exists
    if char.campaign_id:
        await client.delete_relationship(
            "character", character_id, "campaign", "campaign", char.campaign_id
        )

    character_store.delete_character(character_id)
    return {"status": "deleted", "character_id": character_id}
