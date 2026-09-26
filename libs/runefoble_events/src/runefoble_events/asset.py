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


# Register under short class names as well for backward compatibility
register_event(AssetUploaded, event_type="AssetUploaded")
register_event(AssetDeleted, event_type="AssetDeleted")
