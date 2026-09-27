"""FastAPI APIRouter for alchemical crafting and recipe combination.

Part of TASK-0100 / PRD-0014 / US-0044.
"""

from __future__ import annotations

import contextlib
from typing import Any
from uuid import UUID, uuid4

from character_sheet.crafting import (
    CATALYSTS_CATALOGUE,
    KNOWN_RECIPES,
    MISHAP_TABLE,
    REAGENTS_CATALOGUE,
    CraftingAggregate,
    CraftingState,
)
from character_sheet.dependencies import (
    CraftingRepoDep,
    RepoDep,
    SpiceDep,
    UserHeader,
    authorize_character_edit,
    publish_crafting_event,
)
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/crafting", tags=["crafting"])


class CombineReagentsRequest(BaseModel):
    character_id: UUID
    reagents: list[str]
    catalyst: str | None = None
    campaign_id: UUID | str = ""
    session_id: UUID | str = ""
    player_id: str | None = None
    force_mishap: bool = False
    risk_threshold: float = 0.50


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
    user_id: UserHeader = None,
) -> CombineReagentsResponse:
    """Combine alchemical reagents, calculate volatile risk, and update character state."""
    await authorize_character_edit(spicedb, req.character_id, user_id)

    # Load or initialize CraftingAggregate
    try:
        crafting = await crafting_repo.load(req.character_id)
    except Exception:
        crafting = CraftingAggregate(req.character_id)

    # Optional character sheet integration
    char = None
    with contextlib.suppress(Exception):
        char = await char_repo.load(req.character_id)

    # Deduct reagents from character inventory if present
    if char:
        for reagent_name in req.reagents:
            matching_item = next(
                (
                    item
                    for item in char.state.inventory.values()
                    if item.name.lower() == reagent_name.lower()
                ),
                None,
            )
            if matching_item:
                char.remove_inventory_item(matching_item.item_id, quantity=1)

    # Execute crafting domain action
    res = crafting.combine_reagents(
        character_id=req.character_id,
        reagents=req.reagents,
        catalyst=req.catalyst,
        campaign_id=req.campaign_id,
        session_id=req.session_id,
        player_id=req.player_id,
        force_mishap=req.force_mishap,
        risk_threshold=req.risk_threshold,
    )

    events_to_publish = list(crafting.uncommitted_events)
    await crafting_repo.save(crafting)

    # Publish events from crafting aggregate uncommitted events
    for ev in events_to_publish:
        await publish_crafting_event(ev)

    current_hp = None
    conditions = []

    if char:
        if res["outcome"] == "success":
            char.add_inventory_item(
                item_id=str(uuid4()),
                name=res["item_name"],
                quantity=res["quantity"],
                weight_lbs=0.5,
            )
        elif res["outcome"] == "mishap" and res.get("mishap"):
            mishap = res["mishap"]
            if mishap.get("damage", 0) > 0:
                char.modify_health(-mishap["damage"], source="crafting_mishap")
            if mishap.get("condition"):
                char.apply_condition(mishap["condition"], source="crafting_mishap")
        await char_repo.save(char)
        current_hp = char.state.current_hp
        conditions = [
            c if isinstance(c, str) else getattr(c, "name", str(c)) for c in char.state.conditions
        ]

    return CombineReagentsResponse(
        outcome=res["outcome"],
        item_name=res.get("item_name"),
        recipe_name=res.get("recipe_name"),
        quantity=res.get("quantity", 1),
        tags=res.get("tags", []),
        properties=res.get("properties", {}),
        risk_score=res.get("risk_score", 0.0),
        reagents_consumed=res.get("reagents_consumed", []),
        catalyst_consumed=res.get("catalyst_consumed"),
        mishap=res.get("mishap"),
        character_current_hp=current_hp,
        character_conditions=conditions,
    )


@router.get("/{character_id}/history", response_model=CraftingState)
async def get_crafting_history(
    character_id: UUID,
    crafting_repo: CraftingRepoDep,
) -> CraftingState:
    """Retrieve crafting aggregate history and discovered recipes."""
    try:
        crafting = await crafting_repo.load(character_id)
        return crafting.state
    except Exception:
        return CraftingState(character_id=character_id)


__all__ = ["router"]
