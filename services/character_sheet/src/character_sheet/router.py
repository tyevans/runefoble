"""FastAPI APIRouter endpoint controller for Character Sheet microservice."""

from __future__ import annotations

import contextlib
from uuid import UUID

from character_sheet import dependencies as deps
from character_sheet import roster, schemas
from character_sheet.models import CharacterState, StandInGuardrails
from character_sheet.roster import CharacterRosterView
from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter(tags=["character_sheet"])


@router.get("/api/v1/characters", response_model=list[CharacterRosterView])
async def list_characters(
    repo: deps.RepoDep,
    spicedb: deps.SpiceDep,
    user_id: deps.VerifiedUserId,
    campaign_id: str | None = Query(None, alias="campaignId"),
):
    """List the characters the caller may view, optionally one campaign's party."""
    return await roster.visible_characters(repo, spicedb, user_id, campaign_id)


@router.post("/api/v1/characters", response_model=CharacterRosterView)
@router.post("/api/v1/characters/create", response_model=CharacterRosterView)
async def create_character(
    req: schemas.CreateCharacterRequest,
    repo: deps.RepoDep,
    spicedb: deps.SpiceDep,
    user_id: deps.VerifiedUserId,
):
    """Create a character. The verified caller becomes its owner."""
    state = await deps.create_new_character(repo, req)
    with contextlib.suppress(Exception):
        await spicedb.write_relationship(
            "character", str(state.character_id), "owner", "user", user_id
        )
    if req.campaign_id:
        with contextlib.suppress(Exception):
            await spicedb.write_relationship(
                "character", str(state.character_id), "campaign", "campaign", req.campaign_id
            )
    return await roster.roster_view(spicedb, state, owner_id=user_id)


@router.post(
    "/api/v1/characters/{character_id}/level-up",
    dependencies=[Depends(deps.get_principal)],
    response_model=CharacterState,
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
    dependencies=[Depends(deps.get_principal)],
    response_model=CharacterState,
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
    dependencies=[Depends(deps.get_caller_or_service)],
    response_model=CharacterState,
)
async def cast_spell(character_id: UUID, req: schemas.CastSpellRequest, repo: deps.RepoDep):
    return await deps.execute_character_mutation(
        repo, character_id, lambda c: c.cast_spell(req.spell_name, req.slot_level, req.session_id)
    )


@router.post(
    "/api/v1/characters/{character_id}/spells/restore",
    dependencies=[Depends(deps.get_principal)],
    response_model=CharacterState,
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


@router.get("/api/v1/characters/{character_id}", response_model=CharacterRosterView)
async def get_character(
    character_id: UUID,
    repo: deps.RepoDep,
    spicedb: deps.SpiceDep,
    caller: deps.CallerOrService,
):
    """Read one character. A user bearer needs `view`. The service credential reads without a user."""
    state = (await deps.load_character(repo, character_id)).state
    if caller.user_id is not None:
        await deps.authorize_character_permission(spicedb, character_id, "view", caller.user_id)
    return await roster.roster_view(spicedb, state)


@router.post(
    "/api/v1/characters/{character_id}/stand-in",
    dependencies=[Depends(deps.get_principal)],
    response_model=CharacterState,
)
async def set_stand_in_active(
    character_id: UUID, req: schemas.StandInActivationRequest, repo: deps.RepoDep
):
    return await deps.execute_character_mutation(
        repo, character_id, lambda c: c.set_stand_in_active(req.active, req.session_id)
    )


@router.post(
    "/api/v1/characters/{character_id}/health",
    dependencies=[Depends(deps.get_caller_or_service)],
    response_model=CharacterState,
)
async def modify_health(character_id: UUID, req: schemas.HealthChangeRequest, repo: deps.RepoDep):
    try:
        return await deps.modify_character_health(
            repo, character_id, req.delta, req.source, req.is_stand_in, req.session_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/api/v1/characters/{character_id}/penalties",
    dependencies=[Depends(deps.get_caller_or_service)],
    response_model=CharacterState,
)
async def apply_penalty(character_id: UUID, req: schemas.PenaltyRequest, repo: deps.RepoDep):
    return await deps.execute_character_mutation(
        repo,
        character_id,
        lambda c: c.apply_penalty(req.penalty_type, req.description, req.imposed_by),
    )


# fmt: off
@router.delete("/api/v1/characters/{character_id}/penalties/{penalty_type}", dependencies=[Depends(deps.get_principal)], response_model=CharacterState)
async def clear_penalty(character_id: UUID, penalty_type: str, repo: deps.RepoDep):
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.clear_penalty(penalty_type))


@router.post("/api/v1/characters/{character_id}/inventory", dependencies=[Depends(deps.get_principal)], response_model=CharacterState)
@router.post("/api/v1/characters/{character_id}/inventory/add", dependencies=[Depends(deps.get_principal)], response_model=CharacterState)
async def add_inventory_item(character_id: UUID, req: schemas.AddInventoryItemRequest, repo: deps.RepoDep):
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.add_inventory_item(req.item_id, req.name, req.quantity, req.weight_lbs))


@router.delete("/api/v1/characters/{character_id}/inventory/{item_id}", dependencies=[Depends(deps.get_principal)], response_model=CharacterState)
@router.post("/api/v1/characters/{character_id}/inventory/{item_id}/remove", dependencies=[Depends(deps.get_principal)], response_model=CharacterState)
async def remove_inventory_item(character_id: UUID, item_id: str, repo: deps.RepoDep, req: schemas.RemoveInventoryItemRequest | None = None, quantity: int = 1):
    qty = req.quantity if req else quantity
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.remove_inventory_item(item_id, qty))


@router.post("/api/v1/characters/{character_id}/equipment", dependencies=[Depends(deps.get_principal)], response_model=CharacterState)
async def equip_item(character_id: UUID, req: schemas.EquipItemRequest, repo: deps.RepoDep):
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.equip_item(req.slot, req.item_name))


@router.delete("/api/v1/characters/{character_id}/equipment/{slot}", dependencies=[Depends(deps.get_principal)], response_model=CharacterState)
async def unequip_item(character_id: UUID, slot: str, repo: deps.RepoDep):
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.equip_item(slot, None))


@router.post("/api/v1/characters/{character_id}/conditions", dependencies=[Depends(deps.get_caller_or_service)], response_model=CharacterState)
async def apply_condition(character_id: UUID, req: schemas.ApplyConditionRequest, repo: deps.RepoDep):
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.apply_condition(req.condition, req.duration_rounds, req.source))


@router.delete("/api/v1/characters/{character_id}/conditions/{condition}", dependencies=[Depends(deps.get_principal)], response_model=CharacterState)
async def remove_condition(character_id: UUID, condition: str, repo: deps.RepoDep):
    return await deps.execute_character_mutation(repo, character_id, lambda c: c.remove_condition(condition))
# fmt: on


@router.put(
    "/api/v1/characters/{character_id}/guardrails",
    dependencies=[Depends(deps.get_principal)],
    response_model=CharacterState,
)
async def update_guardrails(
    character_id: UUID,
    req: schemas.UpdateGuardrailsRequest,
    repo: deps.RepoDep,
    spicedb: deps.SpiceDep,
    user_id: deps.VerifiedUserId,
):
    await deps.authorize_character_edit(spicedb, character_id, user_id)
    try:
        return await deps.update_character_guardrails(repo, character_id, req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/api/v1/characters/{character_id}/guardrails",
    dependencies=[Depends(deps.get_principal)],
    response_model=StandInGuardrails,
)
async def get_guardrails(character_id: UUID, repo: deps.RepoDep):
    return (await deps.load_character(repo, character_id)).state.stand_in_guardrails


@router.patch("/api/v1/characters/{character_id}/campaign", response_model=CharacterRosterView)
async def assign_campaign(
    character_id: UUID,
    req: schemas.AssignCampaignRequest,
    repo: deps.RepoDep,
    spicedb: deps.SpiceDep,
    user_id: deps.VerifiedUserId,
):
    """Assign or unassign the campaign. Requires `edit`."""
    await deps.authorize_character_edit(spicedb, character_id, user_id)
    state = await deps.assign_character_campaign(
        repo, spicedb, character_id, req.campaign_id, user_id
    )
    return await roster.roster_view(spicedb, state)
