"""Pydantic data transfer models for Asset Forge microservice."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class WallSegment(BaseModel):
    """Line segment representing a solid wall obstacle for line-of-sight and collisions."""

    x1: int
    y1: int
    x2: int
    y2: int
    is_door: bool = False
    wall_type: str = "stone"


class DoorSegment(BaseModel):
    """Portal or doorway connecting rooms/corridors."""

    x1: int
    y1: int
    x2: int
    y2: int
    state: Literal["open", "closed", "locked", "secret"] = "closed"


class HazardCell(BaseModel):
    """Grid coordinate containing hazardous or difficult terrain."""

    x: int
    y: int
    hazard_type: str
    damage_dice: str
    terrain_type: str = "difficult"


class BoardGeometryPayload(BaseModel):
    """Pre-calculated spatial geometry ready for board_state mutators."""

    terrain_mutations: list[dict[str, Any]] = Field(default_factory=list)
    obstacle_tokens: list[dict[str, Any]] = Field(default_factory=list)
    wall_segments: list[dict[str, Any]] = Field(default_factory=list)
    doors: list[dict[str, Any]] = Field(default_factory=list)


class BattlemapForgeRequest(BaseModel):
    """Prompt and configuration parameters for procedural battlemap generation."""

    prompt: str = Field(..., min_length=3, description="Descriptive prompt for the battlemap")
    campaign_id: UUID | None = None
    session_id: str | None = None
    width_cells: int = Field(default=20, ge=5, le=50, description="Grid width in 5-foot squares")
    height_cells: int = Field(default=20, ge=5, le=50, description="Grid height in 5-foot squares")
    cell_size_px: int = Field(default=64, ge=32, le=128, description="Pixels per grid cell")
    theme: str | None = Field(
        default=None, description="Theme override (e.g. dwarven_forge, crypt, forest)"
    )
    wall_density: float = Field(default=0.2, ge=0.0, le=1.0, description="Obstacle density ratio")
    hazard_density: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Hazard pool density ratio"
    )


class BattlemapForgeResponse(BaseModel):
    """Result of procedural battlemap generation and spatial analysis."""

    asset_id: str
    image_url: str
    download_url: str
    width_cells: int
    height_cells: int
    cell_size_px: int
    theme: str
    wall_segments: list[WallSegment]
    hazard_cells: list[HazardCell]
    doors: list[DoorSegment]
    board_geometry_payload: BoardGeometryPayload
    status: str = "forged"


class TokenForgeRequest(BaseModel):
    """Prompt and configuration parameters for procedural character/creature token generation."""

    prompt: str = Field(..., min_length=2, description="Descriptive prompt for token portrait")
    token_name: str = Field(..., min_length=1, description="Name of character or creature")
    token_type: Literal["pc", "npc", "monster", "obstacle"] = "pc"
    campaign_id: UUID | None = None
    size_px: int = Field(
        default=256, ge=64, le=512, description="Pixel dimensions of square canvas"
    )
    crop_style: Literal["circular", "square", "hex"] = "circular"
    border_color: str = Field(default="#e63946", description="Border ring hex color")
    border_width: int = Field(default=8, ge=0, le=32, description="Border ring width in pixels")
    transparent_background: bool = Field(
        default=True, description="Alpha channel transparency outside token border"
    )


class TokenForgeResponse(BaseModel):
    """Result of token portrait synthesis and Silo S3 storage."""

    asset_id: str
    image_url: str
    download_url: str
    token_name: str
    token_type: str
    crop_style: str
    size_px: int
    has_transparency: bool
    status: str = "forged"


class ForgedAssetMetadata(BaseModel):
    """Stored metadata record for forged assets."""

    asset_id: str
    asset_type: Literal["battlemap", "token"]
    prompt: str
    image_url: str
    campaign_id: UUID | None = None
    creator_id: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)
