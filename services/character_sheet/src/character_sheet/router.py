"""FastAPI APIRouter endpoint controller for Character Sheet microservice."""

from __future__ import annotations

from uuid import UUID, uuid4

from character_sheet import dependencies as deps
from character_sheet import roster, schemas
from character_sheet.authz import write_character_ownership
from character_sheet.models import CharacterState
from character_sheet.roster import CharacterRosterView
from fastapi import APIRouter, HTTPException, Query
from runefoble_platform.stand_in_guardrails import StandInGuardrailPolicy

router = APIRouter(tags=["character_sheet"])


@router.get("/api/v1/characters", response_model=list[CharacterRosterView])
async def list_characters(
    repo: deps.RepoDep,
    spicedb: deps.SpiceDep,
    user_id: deps.CallerId,
    campaign_id: str | None = Query(None, alias="campaignId"),
):
    """List the characters the caller may view, optionally one campaign's party."""
    return await roster.visible_characters(repo, spicedb, user_id, campaign_id)


@router.post("/api/v1/characters", response_model=CharacterRosterView)
async def create_character(
    req: schemas.CreateCharacterRequest,
    repo: deps.RepoDep,
    spicedb: deps.SpiceDep,
    user_id: deps.CallerId,
):
    """Create a character. The ownership tuples are written first, so a failed write creates nothing."""
    character_id = uuid4()
    await write_character_ownership(spicedb, character_id, user_id, req.campaign_id)
    state = await deps.create_new_character(repo, req, character_id)
    return await roster.roster_view(spicedb, state, owner_id=user_id)


@router.post(
    "/api/v1/characters/{character_id}/level-up",
    response_model=CharacterState,
    dependencies=deps.EDIT_CHARACTER,
)
async def level_up(
    character_id: UUID, repo: deps.RepoDep, req: schemas.LevelUpRequest | None = None
):
    r = req or schemas.LevelUpRequest()
    return await deps.execute_character_mutation(
        repo, character_id, lambda c: c.level_up(r.target_level, r.hp_increase, r.session_id)
    )


@router.post(
    "/api/v1/characters/{character_id}/spells/prepare",
    response_model=CharacterState,
    dependencies=deps.EDIT_CHARACTER,
)
async def prepare_spell(character_id: UUID, req: schemas.PrepareSpellRequest, repo: deps.RepoDep):
    if not req.is_prepared:
        return await deps.execute_character_mutation(
            repo,
            character_id,
            lambda c: c.unprepare_spell(req.spell_name, req.session_id),
        )
    return await deps.execute_character_mutation(
        repo,
        character_id,
        lambda c: c.prepare_spell(req.spell_name, req.spell_level, req.session_id),
    )


@router.post(
    "/api/v1/characters/{character_id}/spells/cast",
    response_model=CharacterState,
    dependencies=deps.EDIT_CHARACTER_OR_SERVICE,
)
async def cast_spell(character_id: UUID, req: schemas.CastSpellRequest, repo: deps.RepoDep):
    return await deps.execute_character_mutation(
        repo, character_id, lambda c: c.cast_spell(req.spell_name, req.slot_level, req.session_id)
    )


@router.post(
    "/api/v1/characters/{character_id}/spells/restore",
    response_model=CharacterState,
    dependencies=deps.EDIT_CHARACTER,
)
async def restore_spell_slots(
    character_id: UUID,
    repo: deps.RepoDep,
    req: schemas.RestoreSpellSlotsRequest | None = None,
):
    r = req or schemas.RestoreSpellSlotsRequest()
    return await deps.execute_character_mutation(
        repo, character_id, lambda c: c.restore_spell_slots(r.slot_level, r.session_id)
    )


@router.get(
    "/api/v1/characters/{character_id}",
    response_model=CharacterRosterView,
    dependencies=deps.VIEW_CHARACTER,
)
async def get_character(character_id: UUID, repo: deps.RepoDep, spicedb: deps.SpiceDep):
    """Read one character. The caller's user bearer needs `view`. The service credential alone is refused."""
    state = (await deps.load_character(repo, character_id)).state
    return await roster.roster_view(spicedb, state)


@router.post(
    "/api/v1/characters/{character_id}/stand-in",
    response_model=CharacterState,
    dependencies=deps.EDIT_CHARACTER,
)
async def set_stand_in_active(
    character_id: UUID, req: schemas.StandInActivationRequest, repo: deps.RepoDep
):
    return await deps.execute_character_mutation(
        repo, character_id, lambda c: c.set_stand_in_active(req.active, req.session_id)
    )


@router.post(
    "/api/v1/characters/{character_id}/health",
    response_model=CharacterState,
    dependencies=deps.EDIT_CHARACTER_OR_SERVICE,
)
async def modify_health(character_id: UUID, req: schemas.HealthChangeRequest, repo: deps.RepoDep):
    try:
        return await deps.modify_character_health(
            repo, character_id, req.delta, req.source, req.is_stand_in, req.session_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/api/v1/characters/{character_id}/penalties",
    response_model=CharacterState,
    dependencies=deps.EDIT_CHARACTER_OR_SERVICE,
)
async def apply_penalty(character_id: UUID, req: schemas.PenaltyRequest, repo: deps.RepoDep):
    return await deps.execute_character_mutation(
        repo,
        character_id,
        lambda c: c.apply_penalty(req.penalty_type, req.description, req.imposed_by),
    )


# fmt: off
@router.delete("/api/v1/characters/{character_id}/penalties/{penalty_type}", response_model=CharacterState, dependencies=deps.EDIT_CHARACTER)
async def clear_penalty(character_id: UUID, penalty_type: str, repo: deps.RepoDep):
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.clear_penalty(penalty_type))


@router.post("/api/v1/characters/{character_id}/inventory", response_model=CharacterState, dependencies=deps.EDIT_CHARACTER)
async def add_inventory_item(character_id: UUID, req: schemas.AddInventoryItemRequest, repo: deps.RepoDep):
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.add_inventory_item(req.item_id, req.name, req.quantity, req.weight_lbs))


@router.delete("/api/v1/characters/{character_id}/inventory/{item_id}", response_model=CharacterState, dependencies=deps.EDIT_CHARACTER)
async def remove_inventory_item(character_id: UUID, item_id: str, repo: deps.RepoDep, req: schemas.RemoveInventoryItemRequest | None = None, quantity: int = 1):
    qty = req.quantity if req else quantity
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.remove_inventory_item(item_id, qty))


@router.post("/api/v1/characters/{character_id}/equipment", response_model=CharacterState, dependencies=deps.EDIT_CHARACTER)
async def equip_item(character_id: UUID, req: schemas.EquipItemRequest, repo: deps.RepoDep):
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.equip_item(req.slot, req.item_name))


@router.delete("/api/v1/characters/{character_id}/equipment/{slot}", response_model=CharacterState, dependencies=deps.EDIT_CHARACTER)
async def unequip_item(character_id: UUID, slot: str, repo: deps.RepoDep):
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.equip_item(slot, None))


@router.post("/api/v1/characters/{character_id}/conditions", response_model=CharacterState, dependencies=deps.EDIT_CHARACTER_OR_SERVICE)
async def apply_condition(character_id: UUID, req: schemas.ApplyConditionRequest, repo: deps.RepoDep):
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.apply_condition(req.condition, req.duration_rounds, req.source))


@router.delete("/api/v1/characters/{character_id}/conditions/{condition}", response_model=CharacterState, dependencies=deps.EDIT_CHARACTER)
async def remove_condition(character_id: UUID, condition: str, repo: deps.RepoDep):
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.remove_condition(condition))
# fmt: on


@router.put(
    "/api/v1/characters/{character_id}/guardrails",
    response_model=CharacterState,
    dependencies=deps.EDIT_CHARACTER,
)
async def update_guardrails(
    character_id: UUID,
    req: StandInGuardrailPolicy,
    repo: deps.RepoDep,
):
    try:
        return await deps.update_character_guardrails(repo, character_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/api/v1/characters/{character_id}/guardrails",
    response_model=StandInGuardrailPolicy,
    dependencies=deps.VIEW_CHARACTER_OR_SERVICE,
)
async def get_guardrails(character_id: UUID, repo: deps.RepoDep):
    return (await deps.load_character(repo, character_id)).state.stand_in_guardrails


@router.patch(
    "/api/v1/characters/{character_id}/campaign",
    response_model=CharacterRosterView,
    dependencies=deps.EDIT_CHARACTER,
)
async def assign_campaign(
    character_id: UUID,
    req: schemas.AssignCampaignRequest,
    repo: deps.RepoDep,
    spicedb: deps.SpiceDep,
    user_id: deps.CallerId,
):
    state = await deps.assign_character_campaign(
        repo, spicedb, character_id, req.campaign_id, user_id
    )
    return await roster.roster_view(spicedb, state)
