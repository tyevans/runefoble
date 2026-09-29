"""FastAPI APIRouter endpoint controller for Character Sheet microservice."""

from __future__ import annotations

import contextlib
from uuid import UUID

from character_sheet import dependencies as deps
from character_sheet import schemas
from character_sheet.models import CharacterState, StandInGuardrails
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["character_sheet"])


@router.post("/api/v1/characters", response_model=CharacterState)
@router.post("/api/v1/characters/create", response_model=CharacterState)
async def create_character(
    req: schemas.CreateCharacterRequest,
    repo: deps.RepoDep,
    spicedb: deps.SpiceDep,
    x_user_id: deps.UserHeader = None,
):
    owner_id = req.player_id or x_user_id
    state = await deps.create_new_character(repo, req)
    if owner_id:
        with contextlib.suppress(Exception):
            await spicedb.write_relationship(
                "character", str(state.character_id), "owner", "user", owner_id
            )
    if req.campaign_id:
        with contextlib.suppress(Exception):
            await spicedb.write_relationship(
                "character", str(state.character_id), "campaign", "campaign", req.campaign_id
            )
    return state


@router.post("/api/v1/characters/{character_id}/level-up", response_model=CharacterState)
async def level_up(
    character_id: UUID, repo: deps.RepoDep, req: schemas.LevelUpRequest | None = None
):
    r = req or schemas.LevelUpRequest()
    return await deps.execute_character_mutation(
        repo, character_id, lambda c: c.level_up(r.target_level, r.hp_increase, r.session_id)
    )


@router.post("/api/v1/characters/{character_id}/spells/prepare", response_model=CharacterState)
async def prepare_spell(character_id: UUID, req: schemas.PrepareSpellRequest, repo: deps.RepoDep):
    if not req.is_prepared:
        return await deps.execute_character_mutation(
            repo,
            character_id,
            lambda c: c.unprepare_spell(req.spell_name),
        )
    return await deps.execute_character_mutation(
        repo,
        character_id,
        lambda c: c.prepare_spell(req.spell_name, req.spell_level, req.session_id),
    )


@router.post("/api/v1/characters/{character_id}/spells/cast", response_model=CharacterState)
async def cast_spell(character_id: UUID, req: schemas.CastSpellRequest, repo: deps.RepoDep):
    return await deps.execute_character_mutation(
        repo, character_id, lambda c: c.cast_spell(req.spell_name, req.slot_level, req.session_id)
    )


@router.get("/api/v1/characters/{character_id}", response_model=CharacterState)
async def get_character(character_id: UUID, repo: deps.RepoDep):
    return (await deps.load_character(repo, character_id)).state


@router.post("/api/v1/characters/{character_id}/health", response_model=CharacterState)
async def modify_health(character_id: UUID, req: schemas.HealthChangeRequest, repo: deps.RepoDep):
    try:
        return await deps.modify_character_health(
            repo, character_id, req.delta, req.source, req.is_stand_in
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/api/v1/characters/{character_id}/penalties", response_model=CharacterState)
async def apply_penalty(character_id: UUID, req: schemas.PenaltyRequest, repo: deps.RepoDep):
    return await deps.execute_character_mutation(
        repo,
        character_id,
        lambda c: c.apply_penalty(req.penalty_type, req.description, req.imposed_by),
    )


# fmt: off
@router.delete("/api/v1/characters/{character_id}/penalties/{penalty_type}", response_model=CharacterState)
async def clear_penalty(character_id: UUID, penalty_type: str, repo: deps.RepoDep):
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.clear_penalty(penalty_type))


@router.post("/api/v1/characters/{character_id}/inventory", response_model=CharacterState)
@router.post("/api/v1/characters/{character_id}/inventory/add", response_model=CharacterState)
async def add_inventory_item(character_id: UUID, req: schemas.AddInventoryItemRequest, repo: deps.RepoDep):
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.add_inventory_item(req.item_id, req.name, req.quantity, req.weight_lbs))


@router.delete("/api/v1/characters/{character_id}/inventory/{item_id}", response_model=CharacterState)
@router.post("/api/v1/characters/{character_id}/inventory/{item_id}/remove", response_model=CharacterState)
async def remove_inventory_item(character_id: UUID, item_id: str, repo: deps.RepoDep, req: schemas.RemoveInventoryItemRequest | None = None, quantity: int = 1):
    qty = req.quantity if req else quantity
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.remove_inventory_item(item_id, qty))


@router.post("/api/v1/characters/{character_id}/equipment", response_model=CharacterState)
async def equip_item(character_id: UUID, req: schemas.EquipItemRequest, repo: deps.RepoDep):
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.equip_item(req.slot, req.item_name))


@router.delete("/api/v1/characters/{character_id}/equipment/{slot}", response_model=CharacterState)
async def unequip_item(character_id: UUID, slot: str, repo: deps.RepoDep):
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.equip_item(slot, None))


@router.post("/api/v1/characters/{character_id}/conditions", response_model=CharacterState)
async def apply_condition(character_id: UUID, req: schemas.ApplyConditionRequest, repo: deps.RepoDep):
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.apply_condition(req.condition, req.duration_rounds, req.source))


@router.delete("/api/v1/characters/{character_id}/conditions/{condition}", response_model=CharacterState)
async def remove_condition(character_id: UUID, condition: str, repo: deps.RepoDep):
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.remove_condition(condition))
# fmt: on


@router.put("/api/v1/characters/{character_id}/guardrails", response_model=CharacterState)
async def update_guardrails(
    character_id: UUID,
    req: schemas.UpdateGuardrailsRequest,
    repo: deps.RepoDep,
    spicedb: deps.SpiceDep,
    x_user_id: deps.UserHeader = None,
):
    await deps.authorize_character_edit(spicedb, character_id, x_user_id)
    try:
        return await deps.update_character_guardrails(repo, character_id, req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/api/v1/characters/{character_id}/guardrails", response_model=StandInGuardrails)
async def get_guardrails(character_id: UUID, repo: deps.RepoDep):
    return (await deps.load_character(repo, character_id)).state.stand_in_guardrails


@router.patch("/api/v1/characters/{character_id}/campaign", response_model=CharacterState)
async def assign_campaign(
    character_id: UUID,
    req: schemas.AssignCampaignRequest,
    repo: deps.RepoDep,
    spicedb: deps.SpiceDep,
    x_user_id: deps.UserHeader = None,
):
    await deps.authorize_character_edit(spicedb, character_id, x_user_id)
    assigned_by = req.assigned_by or x_user_id or "system"
    return await deps.assign_character_campaign(
        repo, spicedb, character_id, req.campaign_id, assigned_by
    )
