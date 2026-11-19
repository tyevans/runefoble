"""FastAPI APIRouter for alchemical crafting and recipe combination.

Part of TASK-0100 / PRD-0014 / US-0044.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import UUID

from character_sheet.authz import character_denial
from character_sheet.crafting import (
    CATALYSTS_CATALOGUE,
    KNOWN_RECIPES,
    MISHAP_TABLE,
    REAGENTS_CATALOGUE,
    CraftingState,
)
from character_sheet.crafting.service import CharacterNotFoundError, CombineReagentsService
from character_sheet.dependencies import (
    VIEW_CHARACTER,
    CallerId,
    CraftingRepoDep,
    RepoDep,
    SpiceDep,
    get_principal,
    publish_character_event,
    publish_crafting_event,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from runefoble_auth.permissions import require_subject
from runefoble_platform.aggregate_loading import load_if_exists

router = APIRouter(
    prefix="/api/v1/crafting",
    tags=["crafting"],
    dependencies=[Depends(get_principal)],
)


class CombineReagentsRequest(BaseModel):
    character_id: UUID
    reagents: list[str]
    catalyst: str | None = None
    campaign_id: UUID | str = ""
    session_id: UUID | str = ""
    player_id: str | None = None
    force_mishap: bool = False
    risk_threshold: float = 0.50
    # Optional client attempt id. A repeat with the same id spends nothing again and returns the
    # recorded outcome. Without it, every call is a new attempt (TASK-0772).
    attempt_id: UUID | None = None


class CombineReagentsResponse(BaseModel):
    outcome: str
    item_name: str | None = None
    recipe_name: str | None = None
    quantity: int = 1
    tags: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    risk_score: float = 0.0
    reagents_consumed: list[str] = Field(default_factory=list)
    catalyst_consumed: str | None = None
    mishap: dict[str, Any] | None = None
    character_current_hp: int | None = None
    character_conditions: list[str] = Field(default_factory=list)


@router.get("/recipes")
async def list_known_recipes() -> list[dict[str, Any]]:
    """List canonical known alchemical recipes."""
    return [
        {
            "name": r["name"],
            "ingredients": list(r["ingredients"]),
            "tags": r["tags"],
            "description": r["description"],
            "properties": r["properties"],
        }
        for r in KNOWN_RECIPES
    ]


@router.get("/reagents")
async def list_available_reagents() -> dict[str, Any]:
    """List available reagent affinities and catalysts."""
    return {
        "reagents": REAGENTS_CATALOGUE,
        "catalysts": CATALYSTS_CATALOGUE,
        "mishaps": MISHAP_TABLE,
    }


@router.post("/recipes/combine", response_model=CombineReagentsResponse)
async def combine_reagents(
    req: CombineReagentsRequest,
    crafting_repo: CraftingRepoDep,
    char_repo: RepoDep,
    spicedb: SpiceDep,
    user_id: CallerId,
) -> CombineReagentsResponse:
    """Combine alchemical reagents, calculate volatile risk, and update character state."""
    await require_subject(
        spicedb, "character", str(req.character_id), "edit", user_id, denial=character_denial
    )
    service = CombineReagentsService(
        char_repo, crafting_repo, publish_character_event, publish_crafting_event
    )
    try:
        result = await service.combine(
            character_id=req.character_id,
            reagents=req.reagents,
            catalyst=req.catalyst,
            campaign_id=req.campaign_id,
            session_id=req.session_id,
            player_id=req.player_id,
            force_mishap=req.force_mishap,
            risk_threshold=req.risk_threshold,
            attempt_id=req.attempt_id,
        )
    except CharacterNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Character not found: {e}") from e
    return CombineReagentsResponse(**asdict(result))


@router.get(
    "/{character_id}/history",
    response_model=CraftingState,
    dependencies=VIEW_CHARACTER,
)
async def get_crafting_history(
    character_id: UUID,
    crafting_repo: CraftingRepoDep,
) -> CraftingState:
    """Retrieve crafting aggregate history and discovered recipes.

    An empty state answers only for a character with no crafting stream. A store failure
    propagates and answers 503.
    """
    crafting = await load_if_exists(crafting_repo, character_id)
    if crafting is None:
        return CraftingState(character_id=character_id)
    return crafting.state


__all__ = ["router"]
