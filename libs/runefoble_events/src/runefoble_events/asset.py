"""Asset domain events for Silo S3 asset storage."""

from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.asset.uploaded")
class AssetUploaded(BaseRunefobleEvent):
    """Emitted when a media asset (character avatar, battlemap, audio) is uploaded."""

    aggregate_type: str = "Asset"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.asset.uploaded"
    asset_id: str
    bucket: str
    object_key: str
    content_type: str
    byte_size: int
    owner_id: str


@register_event("runefoble.events.asset.deleted")
class AssetDeleted(BaseRunefobleEvent):
    """Emitted when a media asset is deleted from object storage."""

    aggregate_type: str = "Asset"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.asset.deleted"
    asset_id: str
    bucket: str
    object_key: str
    deleted_by: str


@register_event("runefoble.events.asset.battlemap_forged")
class BattlemapForged(BaseRunefobleEvent):
    """Emitted when a tactical battlemap is procedurally forged and uploaded to Silo."""

    aggregate_type: str = "AssetForge"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.asset.battlemap_forged"
    asset_id: str
    campaign_id: UUID | None = None
    session_id: str | None = None
    creator_id: str
    prompt: str
    image_url: str
    width_cells: int
    height_cells: int
    cell_size_px: int = 64
    wall_segments_count: int = 0
    hazard_cells_count: int = 0
    doors_count: int = 0
    theme: str = "dungeon"
    # Layout for board_state. Wall dicts have x1, y1, x2, y2. Hazard dicts have x, y, hazard_type,
    # terrain_type. board_state owns the obstacle rule and the hazard damage table.
    wall_segments: list[dict[str, Any]] = Field(default_factory=list)
    hazard_cells: list[dict[str, Any]] = Field(default_factory=list)


@register_event("runefoble.events.asset.token_forged")
class TokenAssetForged(BaseRunefobleEvent):
    """Emitted when a character or monster token portrait is procedurally forged."""

    aggregate_type: str = "AssetForge"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.asset.token_forged"
    asset_id: str
    campaign_id: UUID | None = None
    creator_id: str
    prompt: str
    token_name: str
    token_type: str = "pc"
    image_url: str
    crop_style: str = "circular"
    transparent_background: bool = True


@register_event("runefoble.events.asset.print_pdf_forged")
class PrintPdfForged(BaseRunefobleEvent):
    """Emitted when a multi-page grid-calibrated PDF or standee sheet is forged."""

    aggregate_type: str = "AssetForge"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.asset.print_pdf_forged"
    asset_id: str
    campaign_id: UUID | None = None
    session_id: str | None = None
    creator_id: str
    total_pages: int
    page_size: str
    grid_scale: str = "1-inch"
    download_url: str


@register_event("runefoble.events.asset.stl_token_forged")
class StlTokenForged(BaseRunefobleEvent):
    """Emitted when a 3D-printable miniature base or condition clip is forged."""

    aggregate_type: str = "AssetForge"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.asset.stl_token_forged"
    asset_id: str
    campaign_id: UUID | None = None
    creator_id: str
    diameter_mm: float
    height_mm: float
    facet_count: int
    condition_label: str = "Poisoned"
    download_url: str
