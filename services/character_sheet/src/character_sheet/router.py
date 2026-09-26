"""FastAPI APIRouter endpoint controller for Character Sheet microservice."""

from __future__ import annotations

from uuid import UUID

from character_sheet.dependencies import (
    RepoDep,
    SpiceDep,
    UserHeader,
    authorize_character_edit,
    create_new_character,
    execute_character_mutation,
    load_character,
    modify_character_health,
    update_character_guardrails,
)
from character_sheet.models import CharacterState, StandInGuardrails
from character_sheet.schemas import (
    AddInventoryItemRequest,
    ApplyConditionRequest,
    CastSpellRequest,
    CreateCharacterRequest,
    EquipItemRequest,
    HealthChangeRequest,
    LevelUpRequest,
    PenaltyRequest,
    PrepareSpellRequest,
    RemoveInventoryItemRequest,
    UpdateGuardrailsRequest,
)
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["character_sheet"])


@router.post("/api/v1/characters", response_model=CharacterState)
@router.post("/api/v1/characters/create", response_model=CharacterState)
async def create_character(req: CreateCharacterRequest, repo: RepoDep):
    return await create_new_character(repo, req)


@router.post("/api/v1/characters/{character_id}/level-up", response_model=CharacterState)
async def level_up(character_id: UUID, repo: RepoDep, req: LevelUpRequest | None = None):
    r = req or LevelUpRequest()
    return await execute_character_mutation(
        repo, character_id, lambda c: c.level_up(r.target_level, r.hp_increase, r.session_id)
    )


@router.post("/api/v1/characters/{character_id}/spells/prepare", response_model=CharacterState)
async def prepare_spell(character_id: UUID, req: PrepareSpellRequest, repo: RepoDep):
    return await execute_character_mutation(
        repo,
        character_id,
        lambda c: c.prepare_spell(req.spell_name, req.spell_level, req.session_id),
    )


@router.post("/api/v1/characters/{character_id}/spells/cast", response_model=CharacterState)
async def cast_spell(character_id: UUID, req: CastSpellRequest, repo: RepoDep):
    return await execute_character_mutation(
        repo, character_id, lambda c: c.cast_spell(req.spell_name, req.slot_level, req.session_id)
    )


@router.get("/api/v1/characters/{character_id}", response_model=CharacterState)
async def get_character(character_id: UUID, repo: RepoDep):
    return (await load_character(repo, character_id)).state


@router.post("/api/v1/characters/{character_id}/health", response_model=CharacterState)
async def modify_health(character_id: UUID, req: HealthChangeRequest, repo: RepoDep):
    try:
        return await modify_character_health(
            repo, character_id, req.delta, req.source, req.is_stand_in
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/api/v1/characters/{character_id}/penalties", response_model=CharacterState)
async def apply_penalty(character_id: UUID, req: PenaltyRequest, repo: RepoDep):
    return await execute_character_mutation(
        repo,
        character_id,
        lambda c: c.apply_penalty(req.penalty_type, req.description, req.imposed_by),
    )


@router.delete(
    "/api/v1/characters/{character_id}/penalties/{penalty_type}", response_model=CharacterState
)
async def clear_penalty(character_id: UUID, penalty_type: str, repo: RepoDep):
    return await execute_character_mutation(
        repo, character_id, lambda c: c.clear_penalty(penalty_type)
    )


@router.post("/api/v1/characters/{character_id}/inventory/add", response_model=CharacterState)
async def add_inventory_item(character_id: UUID, req: AddInventoryItemRequest, repo: RepoDep):
    return await execute_character_mutation(
        repo,
        character_id,
        lambda c: c.add_inventory_item(req.item_id, req.name, req.quantity, req.weight_lbs),
    )


@router.post(
    "/api/v1/characters/{character_id}/inventory/{item_id}/remove", response_model=CharacterState
)
async def remove_inventory_item(
    character_id: UUID, item_id: str, req: RemoveInventoryItemRequest, repo: RepoDep
):
    return await execute_character_mutation(
        repo, character_id, lambda c: c.remove_inventory_item(item_id, req.quantity)
    )


@router.post("/api/v1/characters/{character_id}/equipment", response_model=CharacterState)
async def equip_item(character_id: UUID, req: EquipItemRequest, repo: RepoDep):
    return await execute_character_mutation(
        repo, character_id, lambda c: c.equip_item(req.slot, req.item_name)
    )


@router.post("/api/v1/characters/{character_id}/conditions", response_model=CharacterState)
async def apply_condition(character_id: UUID, req: ApplyConditionRequest, repo: RepoDep):
    return await execute_character_mutation(
        repo,
        character_id,
        lambda c: c.apply_condition(req.condition, req.duration_rounds, req.source),
    )


@router.delete(
    "/api/v1/characters/{character_id}/conditions/{condition}", response_model=CharacterState
)
async def remove_condition(character_id: UUID, condition: str, repo: RepoDep):
    return await execute_character_mutation(
        repo, character_id, lambda c: c.remove_condition(condition)
    )


@router.put("/api/v1/characters/{character_id}/guardrails", response_model=CharacterState)
async def update_guardrails(
    character_id: UUID,
    req: UpdateGuardrailsRequest,
    repo: RepoDep,
    spicedb: SpiceDep,
    x_user_id: UserHeader = None,
):
    await authorize_character_edit(spicedb, character_id, x_user_id)
    try:
        return await update_character_guardrails(repo, character_id, req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/api/v1/characters/{character_id}/guardrails", response_model=StandInGuardrails)
async def get_guardrails(character_id: UUID, repo: RepoDep):
    return (await load_character(repo, character_id)).state.stand_in_guardrails
