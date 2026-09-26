"""Character Sheet Microservice - Powered by eventsource-py.

Manages player and NPC character sheets, hit points, inventories,
equipment, and status conditions (such as DM penalties for missed sessions).
"""

from typing import Literal
from uuid import UUID, uuid4

from character_sheet.aggregate import CharacterAggregate, CharacterState
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
    get_event_store,
)

app = FastAPI(
    title="Runefoble - Character Sheet Service",
    version="0.1.0",
    description="Character Stats, HP Tracking, Inventory, Equipment, and DM Penalties backed by eventsource-py.",
)

# Global aggregate repository
repo: AggregateRepository[CharacterAggregate] = create_aggregate_repository(CharacterAggregate)


class CreateCharacterRequest(BaseModel):
    name: str
    character_class: str
    max_hp: int = 30
    player_id: str | None = None
    personality_traits: list[str] = ["brave", "curious"]


class HealthChangeRequest(BaseModel):
    delta: int
    source: str = "damage"


class PenaltyRequest(BaseModel):
    penalty_type: Literal["drunk", "foolishness", "cowardice", "greed", "curse"]
    description: str
    imposed_by: Literal["human_dm", "the_watcher"] = "the_watcher"


class AddInventoryItemRequest(BaseModel):
    item_id: str
    name: str
    quantity: int = 1
    weight_lbs: float = 0.0


class RemoveInventoryItemRequest(BaseModel):
    quantity: int = 1


class EquipItemRequest(BaseModel):
    slot: str
    item_name: str | None = None


class ApplyConditionRequest(BaseModel):
    condition: str
    duration_rounds: int | None = None
    source: str = ""


class LevelUpRequest(BaseModel):
    target_level: int | None = None
    hp_increase: int | None = None
    session_id: str = ""


class PrepareSpellRequest(BaseModel):
    spell_name: str
    spell_level: int | None = None
    session_id: str = ""


class CastSpellRequest(BaseModel):
    spell_name: str
    slot_level: int | None = None
    session_id: str = ""


@app.get("/healthz")
async def health_check():
    return {
        "status": "ok",
        "service": "character_sheet",
        "event_store": type(get_event_store()).__name__,
    }


@app.post("/api/v1/characters", response_model=CharacterState)
@app.post("/api/v1/characters/create", response_model=CharacterState)
async def create_character(req: CreateCharacterRequest):
    cid = uuid4()
    char = CharacterAggregate(cid)
    char.create(
        name=req.name,
        character_class=req.character_class,
        max_hp=req.max_hp,
        player_id=req.player_id,
        personality_traits=req.personality_traits,
    )
    await repo.save(char)
    return char.state


@app.post("/api/v1/characters/{character_id}/level-up", response_model=CharacterState)
async def level_up(character_id: UUID, req: LevelUpRequest | None = None):
    try:
        char = await repo.load(character_id)
        r = req or LevelUpRequest()
        char.level_up(
            target_level=r.target_level,
            hp_increase=r.hp_increase,
            session_id=r.session_id,
        )
        await repo.save(char)
        return char.state
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/v1/characters/{character_id}/spells/prepare", response_model=CharacterState)
async def prepare_spell(character_id: UUID, req: PrepareSpellRequest):
    try:
        char = await repo.load(character_id)
        char.prepare_spell(
            spell_name=req.spell_name,
            spell_level=req.spell_level,
            session_id=req.session_id,
        )
        await repo.save(char)
        return char.state
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/v1/characters/{character_id}/spells/cast", response_model=CharacterState)
async def cast_spell(character_id: UUID, req: CastSpellRequest):
    try:
        char = await repo.load(character_id)
        char.cast_spell(
            spell_name=req.spell_name,
            slot_level=req.slot_level,
            session_id=req.session_id,
        )
        await repo.save(char)
        return char.state
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/v1/characters/{character_id}", response_model=CharacterState)
async def get_character(character_id: UUID):
    try:
        char = await repo.load(character_id)
        return char.state
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Character not found: {e}") from e


@app.post("/api/v1/characters/{character_id}/health", response_model=CharacterState)
async def modify_health(character_id: UUID, req: HealthChangeRequest):
    try:
        char = await repo.load(character_id)
        char.modify_health(delta=req.delta, source=req.source)
        await repo.save(char)
        return char.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/v1/characters/{character_id}/penalties", response_model=CharacterState)
async def apply_penalty(character_id: UUID, req: PenaltyRequest):
    """Assign a status condition or DM session miss penalty to a character."""
    try:
        char = await repo.load(character_id)
        char.apply_penalty(
            penalty_type=req.penalty_type,
            description=req.description,
            imposed_by=req.imposed_by,
        )
        await repo.save(char)
        return char.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.delete(
    "/api/v1/characters/{character_id}/penalties/{penalty_type}", response_model=CharacterState
)
async def clear_penalty(character_id: UUID, penalty_type: str):
    """Clear an active penalty from a character."""
    try:
        char = await repo.load(character_id)
        char.clear_penalty(penalty_type=penalty_type)
        await repo.save(char)
        return char.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/v1/characters/{character_id}/inventory/add", response_model=CharacterState)
async def add_inventory_item(character_id: UUID, req: AddInventoryItemRequest):
    try:
        char = await repo.load(character_id)
        char.add_inventory_item(
            item_id=req.item_id,
            name=req.name,
            quantity=req.quantity,
            weight_lbs=req.weight_lbs,
        )
        await repo.save(char)
        return char.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post(
    "/api/v1/characters/{character_id}/inventory/{item_id}/remove", response_model=CharacterState
)
async def remove_inventory_item(character_id: UUID, item_id: str, req: RemoveInventoryItemRequest):
    try:
        char = await repo.load(character_id)
        char.remove_inventory_item(item_id=item_id, quantity=req.quantity)
        await repo.save(char)
        return char.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/v1/characters/{character_id}/equipment", response_model=CharacterState)
async def equip_item(character_id: UUID, req: EquipItemRequest):
    try:
        char = await repo.load(character_id)
        char.equip_item(slot=req.slot, item_name=req.item_name)
        await repo.save(char)
        return char.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/v1/characters/{character_id}/conditions", response_model=CharacterState)
async def apply_condition(character_id: UUID, req: ApplyConditionRequest):
    try:
        char = await repo.load(character_id)
        char.apply_condition(
            condition=req.condition,
            duration_rounds=req.duration_rounds,
            source=req.source,
        )
        await repo.save(char)
        return char.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.delete(
    "/api/v1/characters/{character_id}/conditions/{condition}", response_model=CharacterState
)
async def remove_condition(character_id: UUID, condition: str):
    try:
        char = await repo.load(character_id)
        char.remove_condition(condition=condition)
        await repo.save(char)
        return char.state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/ui/manifest")
def get_ui_manifest():
    """Advertise vendored microfrontend components for character sheet."""
    return {
        "service": "character_sheet",
        "package": "@runefoble/character-sheet-ui",
        "components": ["runefoble-character-card", "runefoble-absentee-recap"],
        "version": "0.1.0",
    }


def main():
    import uvicorn

    uvicorn.run("character_sheet.main:app", host="0.0.0.0", port=8003, reload=True)


if __name__ == "__main__":
    main()
