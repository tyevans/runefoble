"""FastAPI APIRouter for Character Wardrobe and Dynamic Portrait Gallery."""

from __future__ import annotations

from uuid import UUID

from character_sheet.dependencies import (
    RepoDep,
    SpiceDep,
    UserHeader,
    authorize_character_edit,
    load_character,
    publish_character_event,
)
from character_sheet.models import CharacterState, WardrobeVariant
from character_sheet.portrait import compose_portrait_svg
from character_sheet.schemas import (
    AddWardrobeVariantRequest,
    PortraitResponse,
    SetActivePortraitRequest,
)
from fastapi import APIRouter
from runefoble_events.events import CharacterPortraitUpdated, PortraitVariantGenerated

router = APIRouter(tags=["character_wardrobe"])


@router.get("/api/v1/characters/{character_id}/portrait", response_model=PortraitResponse)
async def get_portrait(character_id: UUID, repo: RepoDep) -> PortraitResponse:
    """Retrieve active and base portrait URLs, condition badges, and composited SVG."""
    char = await load_character(repo, character_id)
    state = char.state
    svg = compose_portrait_svg(
        state.base_portrait_url, state.current_hp, state.max_hp, state.conditions
    )
    return PortraitResponse(
        character_id=str(state.character_id),
        active_portrait_url=state.active_portrait_url,
        base_portrait_url=state.base_portrait_url,
        active_variant_id=state.active_variant_id,
        condition_badges=state.condition_badges,
        svg_overlay=svg,
        current_hp=state.current_hp,
        max_hp=state.max_hp,
    )


@router.post("/api/v1/characters/{character_id}/portrait/active", response_model=CharacterState)
async def set_active_portrait(
    character_id: UUID,
    req: SetActivePortraitRequest,
    repo: RepoDep,
    spicedb: SpiceDep,
    x_user_id: UserHeader = None,
) -> CharacterState:
    """Assign active portrait avatar from an unlocked wardrobe variant or custom image URL."""
    await authorize_character_edit(spicedb, character_id, x_user_id)
    char = await load_character(repo, character_id)
    char.set_active_portrait(req.variant_id, req.image_url)
    await repo.save(char)
    await publish_character_event(
        CharacterPortraitUpdated(
            aggregate_id=character_id,
            character_id=str(character_id),
            active_portrait_url=char.state.active_portrait_url,
            variant_id=req.variant_id,
        )
    )
    return char.state


@router.get("/api/v1/characters/{character_id}/wardrobe", response_model=dict[str, WardrobeVariant])
async def get_wardrobe(character_id: UUID, repo: RepoDep) -> dict[str, WardrobeVariant]:
    """Retrieve all unlocked wardrobe attire variants for a character."""
    return (await load_character(repo, character_id)).state.wardrobe_variants


@router.post("/api/v1/characters/{character_id}/wardrobe", response_model=CharacterState)
async def add_wardrobe_variant(
    character_id: UUID,
    req: AddWardrobeVariantRequest,
    repo: RepoDep,
    spicedb: SpiceDep,
    x_user_id: UserHeader = None,
) -> CharacterState:
    """Add a synthesized or unlocked wardrobe variant and optionally set active."""
    await authorize_character_edit(spicedb, character_id, x_user_id)
    char = await load_character(repo, character_id)
    vid = char.add_wardrobe_variant(
        variant_name=req.variant_name,
        attire_type=req.attire_type,
        image_url=req.image_url,
        prompt=req.prompt,
        variant_id=req.variant_id,
        set_active=req.set_active,
    )
    await repo.save(char)
    await publish_character_event(
        PortraitVariantGenerated(
            aggregate_id=character_id,
            character_id=str(character_id),
            variant_id=vid,
            variant_name=req.variant_name,
            attire_type=req.attire_type,
            image_url=req.image_url,
            prompt=req.prompt,
            is_active=req.set_active,
        )
    )
    if req.set_active:
        await publish_character_event(
            CharacterPortraitUpdated(
                aggregate_id=character_id,
                character_id=str(character_id),
                active_portrait_url=char.state.active_portrait_url,
                variant_id=vid,
            )
        )
    return char.state
