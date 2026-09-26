"""Pydantic request and response models for Gateway API endpoints."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class AssignRoleRequest(BaseModel):
    user_id: str
    role: Literal["owner", "dungeon_master", "player", "spectator"]


class AdvanceTurnRequest(BaseModel):
    next_character_id: str


class DMOverrideRequest(BaseModel):
    action: str
    reason: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class AtmosphereUpdateRequest(BaseModel):
    location_name: str
    lighting: str = "Normal"
    mood: str = "Neutral"
    description: str = ""
    ambient_audio_prompt: str | None = None


class TokenMoveRequest(BaseModel):
    to_x: int
    to_y: int


class UpgradeStrongholdGatewayRequest(BaseModel):
    facility_id: str
    gold_spent: int = 0
    materials_spent: dict[str, int] = Field(default_factory=dict)


class CampfireRestGatewayRequest(BaseModel):
    rest_type: Literal["short", "long"] = "long"
    storytelling_prompt: str | None = None
    participating_character_ids: list[str] = Field(default_factory=list)


class CombineReagentsGatewayRequest(BaseModel):
    character_id: str
    reagents: list[str]
    catalyst: str | None = None
    force_mishap: bool = False


class StartMinigameGatewayRequest(BaseModel):
    game_type: Literal["liars_dice", "card_duel", "drinking_contest"] = "liars_dice"
    wager_gold: int = 10
    initiator_id: str
    challenger_id: str = "npc_pirate"


class HaggleGatewayRequest(BaseModel):
    character_id: str
    item_name: str
    base_price: int
    offered_price: int
    charisma_modifier: int = 0
    dialogue: str = ""
    temperament: str = "stubborn_greedy"
