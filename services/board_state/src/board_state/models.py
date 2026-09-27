"""Pydantic state schemas and API request/response models for Board State microservice."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TerrainCellState(BaseModel):
    x: int
    y: int
    elevation: int = 0
    terrain_type: str = "normal"
    hazard: str | None = None
    hazard_status: str | None = None


class TerrainDict(dict):
    """Dictionary supporting both 'x,y' string keys and (x, y) tuple keys."""

    def __getitem__(self, key):
        if isinstance(key, tuple):
            return super().__getitem__(f"{key[0]},{key[1]}")
        return super().__getitem__(key)

    def __setitem__(self, key, value):
        if isinstance(key, tuple):
            super().__setitem__(f"{key[0]},{key[1]}", value)
        else:
            super().__setitem__(key, value)

    def __contains__(self, key):
        if isinstance(key, tuple):
            return super().__contains__(f"{key[0]},{key[1]}")
        return super().__contains__(key)

    def get(self, key, default=None):
        if isinstance(key, tuple):
            return super().get(f"{key[0]},{key[1]}", default)
        return super().get(key, default)


class PlacedTokenState(BaseModel):
    token_id: str
    name: str
    token_type: Literal["pc", "monster", "npc", "obstacle"] = "pc"
    x: int
    y: int
    hp: int | None = None
    is_friendly: bool = False
    vision_radius: int = 2
    active_hazard: str | None = None
    hazard_status: str | None = None

    @classmethod
    def from_placed_event(cls, event: Any, hazard: str | None = None) -> PlacedTokenState:
        return cls(
            token_id=str(event.token_id),
            name=event.name,
            token_type=event.token_type,
            x=event.x,
            y=event.y,
            hp=event.hp,
            is_friendly=event.is_friendly,
            active_hazard=hazard,
            hazard_status="active" if hazard else None,
        )


class BoardDecalState(BaseModel):
    decal_id: str
    x: int
    y: int
    decal_type: str = "scorched_earth"
    duration_rounds: int = 2
    rounds_remaining: int = 2
    opacity: float = 1.0


class BoardState(BaseModel):
    board_id: UUID
    session_id: str = ""
    cols: int = 12
    rows: int = 12
    tokens: dict[str, PlacedTokenState] = Field(default_factory=dict)
    terrain_cells: dict[str, TerrainCellState] = Field(default_factory=TerrainDict)
    active_hazards: list[str] = Field(default_factory=list)
    active_decals: list[BoardDecalState] = Field(default_factory=list)
    fog_of_war_enabled: bool = True
    revealed_cells: list[list[int]] = Field(default_factory=list)
    background_asset_id: str | None = None
    background_image_url: str | None = None
    wall_segments: list[dict[str, Any]] = Field(default_factory=list)
    portals: list[dict[str, Any]] = Field(default_factory=list)
    lights: list[dict[str, Any]] = Field(default_factory=list)
    pixels_per_grid: int = 70

    @classmethod
    def initial(cls, board_id: UUID, session_id: str, cols: int, rows: int) -> BoardState:
        return cls(board_id=board_id, session_id=session_id, cols=cols, rows=rows)

    def with_map_imported(
        self,
        cols: int,
        rows: int,
        pixels_per_grid: int = 70,
        background_asset_id: str | None = None,
        background_image_url: str | None = None,
        wall_segments: list[dict[str, Any]] | None = None,
        portals: list[dict[str, Any]] | None = None,
        lights: list[dict[str, Any]] | None = None,
    ) -> BoardState:
        return self.model_copy(
            update={
                "cols": cols,
                "rows": rows,
                "pixels_per_grid": pixels_per_grid,
                "background_asset_id": background_asset_id,
                "background_image_url": background_image_url,
                "wall_segments": wall_segments if wall_segments is not None else self.wall_segments,
                "portals": portals if portals is not None else self.portals,
                "lights": lights if lights is not None else self.lights,
            }
        )

    def with_terrain_modified_from_event(self, event: Any) -> BoardState:
        return self.with_terrain_modified(
            x=event.x,
            y=event.y,
            elevation=event.elevation,
            terrain_type=event.terrain_type,
            hazard=event.hazard,
        )

    def with_terrain_modified(
        self, x: int, y: int, elevation: int, terrain_type: str, hazard: str | None
    ) -> BoardState:
        cells = TerrainDict(self.terrain_cells)
        hazard_status = "active" if hazard else None
        cell_state = TerrainCellState(
            x=x,
            y=y,
            elevation=elevation,
            terrain_type=terrain_type,
            hazard=hazard,
            hazard_status=hazard_status,
        )
        cells[(x, y)] = cell_state
        active_hazards = sorted({c.hazard for c in cells.values() if c.hazard})
        return self.model_copy(update={"terrain_cells": cells, "active_hazards": active_hazards})

    def with_hazard_triggered(self, token_id: str, hazard_type: str) -> BoardState:
        tokens = dict(self.tokens)
        tid = str(token_id)
        if tid in tokens:
            tokens[tid] = tokens[tid].model_copy(
                update={"active_hazard": hazard_type, "hazard_status": "active"}
            )
        return self.model_copy(update={"tokens": tokens})

    def with_token_placed(self, token: PlacedTokenState) -> BoardState:
        tokens = dict(self.tokens)
        tokens[str(token.token_id)] = token
        return self.model_copy(update={"tokens": tokens})

    def with_token_moved(
        self, token_id: str, to_x: int, to_y: int, active_hazard: str | None
    ) -> BoardState:
        tokens = dict(self.tokens)
        tid_str = str(token_id)
        if tid_str in tokens:
            h_status = "active" if active_hazard else None
            tokens[tid_str] = tokens[tid_str].model_copy(
                update={
                    "x": to_x,
                    "y": to_y,
                    "active_hazard": active_hazard,
                    "hazard_status": h_status,
                }
            )
        return self.model_copy(update={"tokens": tokens})

    def without_token(self, token_id: str) -> BoardState:
        tokens = dict(self.tokens)
        tokens.pop(str(token_id), None)
        return self.model_copy(update={"tokens": tokens})

    def with_fog_revealed(self, new_cells: list[list[int]]) -> BoardState:
        existing = {tuple(c) for c in self.revealed_cells}
        for cell in new_cells:
            existing.add(tuple(cell))
        ordered = [list(c) for c in sorted(existing)]
        return self.model_copy(update={"revealed_cells": ordered})

    def with_fog_shrouded(self, shrouded_cells: list[list[int]]) -> BoardState:
        to_remove = {tuple(c) for c in shrouded_cells}
        remaining = [c for c in self.revealed_cells if tuple(c) not in to_remove]
        return self.model_copy(update={"revealed_cells": remaining})

    def with_area_effect(
        self,
        affected_cells: list[list[int]],
        decal_type: str | None = "scorched_earth",
        decal_duration_rounds: int = 2,
    ) -> BoardState:
        decals = list(self.active_decals)
        if decal_type:
            for cell in affected_cells:
                cx, cy = cell[0], cell[1]
                decals.append(
                    BoardDecalState(
                        decal_id=f"decal-{uuid4().hex[:8]}",
                        x=cx,
                        y=cy,
                        decal_type=decal_type,
                        duration_rounds=decal_duration_rounds,
                        rounds_remaining=decal_duration_rounds,
                        opacity=1.0,
                    )
                )
        return self.model_copy(update={"active_decals": decals})

    def with_decals_decayed(self, rounds: int = 1) -> BoardState:
        updated = []
        for d in self.active_decals:
            rem = d.rounds_remaining - rounds
            if rem > 0:
                updated.append(
                    d.model_copy(
                        update={
                            "rounds_remaining": rem,
                            "opacity": max(0.2, rem / d.duration_rounds),
                        }
                    )
                )
        return self.model_copy(update={"active_decals": updated})


class CreateBoardRequest(BaseModel):
    session_id: str | None = None
    board_id: str | None = None
    cols: int | None = None
    rows: int | None = None
    width: int | None = None
    height: int | None = None


class ConfigureTerrainRequest(BaseModel):
    x: int
    y: int
    elevation: int = 0
    terrain_type: str = "normal"
    hazard: str | None = None


class PlaceTokenRequest(BaseModel):
    token_id: str | None = None
    name: str
    token_type: Literal["pc", "monster", "npc", "obstacle"] = "pc"
    x: int
    y: int
    hp: int | None = None
    is_friendly: bool = True
    vision_radius: int = 2


class MoveTokenRequest(BaseModel):
    token_id: str | None = None
    to_x: int
    to_y: int
    initiated_by: Literal["player", "the_watcher", "stand_in"] = "player"
    movement_budget: int | None = None


class MoveTokenResponse(BaseModel):
    token_id: str
    name: str
    token_type: Literal["pc", "monster", "npc", "obstacle"] = "pc"
    x: int
    y: int
    hp: int | None = None
    is_friendly: bool = False
    vision_radius: int = 2
    active_hazard: str | None = None
    hazard_status: str | None = None
    movement_cost: int = 1
    hazard_triggered: str | None = None
    damage_dice: str | None = None


class VisibilityResponse(BaseModel):
    session_id: str
    cols: int
    rows: int
    fog_of_war_enabled: bool
    revealed_cells: list[list[int]]
    currently_visible_cells: list[list[int]]
    tokens: list[PlacedTokenState]


class FogOfWarUpdateRequest(BaseModel):
    cells: list[list[int]]
    token_id: str | None = None


class UVTTImportResponse(BaseModel):
    board_id: UUID
    session_id: str = ""
    cols: int
    rows: int
    pixels_per_grid: int = 70
    wall_segments: list[dict[str, Any]] = Field(default_factory=list)
    portals: list[dict[str, Any]] = Field(default_factory=list)
    lights: list[dict[str, Any]] = Field(default_factory=list)
    background_image_url: str | None = None
    background_asset_id: str | None = None
    tokens: dict[str, PlacedTokenState] = Field(default_factory=dict)
    status: str = "imported"


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
