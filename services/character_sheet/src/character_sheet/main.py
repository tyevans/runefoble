"""Character Sheet Microservice - Powered by eventsource-py.

Manages player and NPC character sheets, hit points, inventories,
and status conditions (such as DM penalties for missed sessions).
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
    description="Character Stats, HP Tracking, Inventory, and DM Absence Penalties backed by eventsource-py.",
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


@app.get("/healthz")
async def health_check():
    return {
        "status": "ok",
        "service": "character_sheet",
        "event_store": type(get_event_store()).__name__,
    }


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


def main():
    import uvicorn

    uvicorn.run("character_sheet.main:app", host="0.0.0.0", port=8003, reload=True)


if __name__ == "__main__":
    main()
