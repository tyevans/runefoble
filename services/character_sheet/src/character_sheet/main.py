"""Character Sheet Microservice.

Manages player and NPC character sheets, hit points, inventories,
and status conditions (such as DM penalties for missed sessions).
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Runefoble - Character Sheet Service",
    version="0.1.0",
    description="Character Stats, HP Tracking, Inventory, and DM Absence Penalties.",
)


class CharacterCondition(BaseModel):
    id: str
    name: str
    severity: str = "minor"
    source: str = "normal"  # "session_penalty", "spell", "injury"
    description: str


class CharacterSheet(BaseModel):
    id: str
    campaign_id: str
    name: str
    character_class: str
    level: int = 1
    current_hp: int
    max_hp: int
    armor_class: int = 10
    initiative_bonus: int = 0
    speed: int = 30
    is_ai_stand_in: bool = False
    conditions: list[CharacterCondition] = Field(default_factory=list)


# In-memory characters store
characters: dict[str, CharacterSheet] = {
    "c1": CharacterSheet(
        id="c1",
        campaign_id="camp1",
        name="Valeros",
        character_class="Fighter",
        level=4,
        current_hp=38,
        max_hp=44,
        armor_class=18,
        initiative_bonus=2,
        speed=30,
    ),
    "c2": CharacterSheet(
        id="c2",
        campaign_id="camp1",
        name="Kyra",
        character_class="Cleric",
        level=4,
        current_hp=26,
        max_hp=32,
        armor_class=16,
        initiative_bonus=0,
        speed=25,
        is_ai_stand_in=True,
        conditions=[
            CharacterCondition(
                id="pen1",
                name="Drunk",
                severity="moderate",
                source="session_penalty",
                description="Missed session penalty: Kyra imbibed too heavily before the quest. Disadvantage on perception checks.",
            ),
            CharacterCondition(
                id="pen2",
                name="Foolishness",
                severity="minor",
                source="session_penalty",
                description="Missed session penalty: The AI stand-in acts with boastful overconfidence.",
            ),
        ],
    ),
}


@app.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "character_sheet"}


@app.get("/api/v1/characters/{character_id}", response_model=CharacterSheet)
async def get_character(character_id: str):
    if character_id not in characters:
        raise HTTPException(status_code=404, detail="Character not found")
    return characters[character_id]


@app.post("/api/v1/characters/{character_id}/conditions", response_model=CharacterSheet)
async def apply_condition(character_id: str, condition: CharacterCondition):
    """Assign a status condition or DM session miss penalty to a character."""
    if character_id not in characters:
        raise HTTPException(status_code=404, detail="Character not found")
    char = characters[character_id]
    char.conditions.append(condition)
    return char


def main():
    import uvicorn

    uvicorn.run("character_sheet.main:app", host="0.0.0.0", port=8003, reload=True)


if __name__ == "__main__":
    main()
