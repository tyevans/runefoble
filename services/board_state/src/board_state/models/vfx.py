"""Visual effects, spell animations, and board decal schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BoardDecalState(BaseModel):
    decal_id: str
    x: int
    y: int
    decal_type: str = "scorched_earth"
    duration_rounds: int = 2
    rounds_remaining: int = 2
    opacity: float = 1.0


class CastSpellRequest(BaseModel):
    caster_token_id: str | None = None
    spell_name: str
    spell_archetype: Literal[
        "evocation",
        "abjuration",
        "conjuration",
        "transmutation",
        "necromancy",
        "enchantment",
        "illusion",
        "divination",
    ] = "evocation"
    target_x: int
    target_y: int
    origin_x: int | None = None
    origin_y: int | None = None
    radius_ft: int = 20
    damage_dice: str | None = None
    damage_type: str | None = None
    theme_palette: str | None = None


class CastSpellResponse(BaseModel):
    animation_id: str
    session_id: str
    spell_name: str
    spell_archetype: str
    caster_token_id: str | None = None
    origin_x: int | None = None
    origin_y: int | None = None
    target_x: int
    target_y: int
    radius_ft: int = 20
    trajectory: list[list[float]] = Field(default_factory=list)
    affected_token_ids: list[str] = Field(default_factory=list)
    affected_cells: list[list[int]] = Field(default_factory=list)
    decal_type: str | None = None
    status: str = "launched"
    audio_stinger: str = "evocation_fireball_stinger"
    duration_ms: int = 500


class FinishVFXRequest(BaseModel):
    animation_id: str
    spell_name: str
    target_x: int
    target_y: int
    duration_ms: int = 500


class FinishVFXResponse(BaseModel):
    animation_id: str
    status: str = "finished"


class DecayDecalsRequest(BaseModel):
    rounds: int = 1
