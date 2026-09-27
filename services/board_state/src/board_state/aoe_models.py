"""AoE template and radial token action data models for Board State microservice."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AoETemplateState(BaseModel):
    template_id: str
    caster_token_id: str | None = None
    shape: str = "cone"
    origin_x: float
    origin_y: float
    direction_deg: float = 0.0
    radius_ft: float | None = None
    length_ft: float | None = None
    width_ft: float | None = 5.0
    spell_name: str | None = None
    affected_token_ids: list[str] = Field(default_factory=list)
    affected_cells: list[list[int]] = Field(default_factory=list)


class TokenActionRequest(BaseModel):
    token_id: str | None = None
    action: str  # "attack", "dodge", "dash", "disengage", "cast"
    target_token_id: str | None = None
    target_token_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    initiated_by: Literal["player", "the_watcher", "stand_in"] = "player"


class TokenActionResponse(BaseModel):
    token_id: str
    action: str
    status: str = "executed"
    target_token_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    message: str = ""


class AoEEvaluateRequest(BaseModel):
    template_id: str | None = None
    caster_token_id: str | None = None
    shape: str = "cone"  # "cone", "sphere", "line", "cube"
    origin_x: float
    origin_y: float
    direction_deg: float = 0.0
    radius_ft: float | None = 15.0
    length_ft: float | None = None
    width_ft: float | None = 5.0
    spell_name: str | None = None
    grid_type: Literal["square", "hex"] = "square"


class AoETemplatePlaceRequest(BaseModel):
    template_id: str | None = None
    caster_token_id: str | None = None
    shape: str = "cone"
    origin_x: float
    origin_y: float
    direction_deg: float = 0.0
    radius_ft: float | None = 15.0
    length_ft: float | None = None
    width_ft: float | None = 5.0
    spell_name: str | None = None
    grid_type: Literal["square", "hex"] = "square"


class AoETemplateResponse(BaseModel):
    template_id: str
    caster_token_id: str | None = None
    shape: str
    origin_x: float
    origin_y: float
    direction_deg: float
    radius_ft: float | None = None
    length_ft: float | None = None
    width_ft: float | None = None
    spell_name: str | None = None
    affected_token_ids: list[str] = Field(default_factory=list)
    affected_tokens: list[Any] = Field(default_factory=list)
    affected_cells: list[list[int]] = Field(default_factory=list)
