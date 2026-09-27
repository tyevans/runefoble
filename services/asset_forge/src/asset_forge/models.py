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
    asset_type: Literal["battlemap", "token", "print_pdf", "standees", "stl_token"]
    prompt: str
    image_url: str
    campaign_id: UUID | None = None
    creator_id: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class PrintPdfRequest(BaseModel):
    """Request model for generating multi-page grid-calibrated battlemap PDFs."""

    prompt: str | None = Field(default=None, description="Prompt or name of the map")
    campaign_id: UUID | None = None
    session_id: str | None = None
    width_cells: int = Field(default=16, ge=4, le=100)
    height_cells: int = Field(default=16, ge=4, le=100)
    page_size: Literal["letter", "a4"] = "letter"
    theme: str = "dwarven_forge"
    grid: list[list[int]] | None = None
    format: Literal["binary", "json"] = "binary"
    title: str = "Tactical Battlemap"


class PrintPdfResponse(BaseModel):
    """Metadata response for generated multi-page tiled PDF."""

    asset_id: str
    download_url: str
    total_pages: int
    rows: int
    cols: int
    page_size: str
    grid_calibration: str = "1-inch (72pt)"
    status: str = "forged"


class StandeeItem(BaseModel):
    """Configuration for a single papercraft standee miniature."""

    name: str
    type: Literal["pc", "npc", "monster", "obstacle"] = "pc"
    hp: int = 10
    color: str = "#2a9d8f"


class StandeesRequest(BaseModel):
    """Request model for generating folding papercraft miniature sheets."""

    standees: list[StandeeItem] = Field(default_factory=list)
    page_size: Literal["letter", "a4"] = "letter"
    sheet_title: str = "Runefoble Tabletop Standees"
    campaign_id: UUID | None = None
    format: Literal["binary", "json"] = "binary"


class StandeesResponse(BaseModel):
    """Metadata response for generated papercraft standees sheet."""

    asset_id: str
    download_url: str
    standee_count: int
    pages: int
    page_size: str
    status: str = "forged"


class StlTokenRequest(BaseModel):
    """Request model for generating 3D printable STL miniature bases and condition clips."""

    diameter_mm: float = Field(default=28.0, ge=15.0, le=100.0)
    height_mm: float = Field(default=3.5, ge=2.0, le=20.0)
    num_slots: int = Field(default=4, ge=0, le=12)
    slot_depth_mm: float = Field(default=1.5, ge=0.5, le=5.0)
    condition_label: str = "Poisoned"
    binary: bool = True
    campaign_id: UUID | None = None
    format: Literal["binary", "json"] = "binary"


class StlTokenResponse(BaseModel):
    """Metadata response for generated 3D printable STL token base."""

    asset_id: str
    download_url: str
    diameter_mm: float
    height_mm: float
    facet_count: int
    is_watertight: bool = True
    condition_label: str
    status: str = "forged"


class WardrobeForgeRequest(BaseModel):
    """Prompt and configuration parameters for generative character wardrobe synthesis."""

    character_id: UUID | str = Field(..., description="ID of character receiving wardrobe variant")
    character_name: str = Field(..., min_length=1, description="Name of character")
    attire_type: str = Field(
        default="ballroom_masquerade",
        description="Thematic attire style: ballroom_masquerade, arctic_tundra, tavern_casual, battle_damaged, ceremonial",
    )
    prompt: str | None = Field(default=None, description="Optional custom prompt additions")
    campaign_id: UUID | None = None
    face_embedding_seed: str | None = None
    border_color: str = Field(default="#e63946", description="Border ring hex color")
    size_px: int = Field(default=256, ge=64, le=512, description="Square pixel dimensions")


class WardrobeForgeResponse(BaseModel):
    """Result of generative wardrobe synthesis and Silo S3 storage."""

    variant_id: str
    character_id: str
    variant_name: str
    attire_type: str
    image_url: str
    download_url: str
    prompt: str
    status: str = "forged"
