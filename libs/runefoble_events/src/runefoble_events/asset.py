"""Asset domain events for Silo S3 asset storage."""

from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.asset.uploaded")
class AssetUploaded(BaseRunefobleEvent):
    """Emitted when a media asset (character avatar, battlemap, audio) is uploaded."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Asset"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.asset.uploaded"
    asset_id: str
    bucket: str
    object_key: str
    content_type: str
    byte_size: int
    owner_id: str
    url: str


@register_event("runefoble.events.asset.deleted")
class AssetDeleted(BaseRunefobleEvent):
    """Emitted when a media asset is deleted from object storage."""

    suppress_event_type_warning: ClassVar[bool] = True
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

    suppress_event_type_warning: ClassVar[bool] = True
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


@register_event("runefoble.events.asset.token_forged")
class TokenAssetForged(BaseRunefobleEvent):
    """Emitted when a character or monster token portrait is procedurally forged."""

    suppress_event_type_warning: ClassVar[bool] = True
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


# Register under short class names and aliases as well for backward compatibility
register_event(AssetUploaded, event_type="AssetUploaded")
register_event(AssetDeleted, event_type="AssetDeleted")
register_event(BattlemapForged, event_type="BattlemapForged")
register_event(BattlemapForged, event_type="BattlemapCreated")
register_event(TokenAssetForged, event_type="TokenAssetForged")
register_event(TokenAssetForged, event_type="AssetGenerated")

# Legacy aliases
BattlemapCreated = BattlemapForged
AssetGenerated = TokenAssetForged
