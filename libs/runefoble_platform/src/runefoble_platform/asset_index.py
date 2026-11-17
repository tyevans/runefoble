"""Durable asset index: event-sourced record of every Silo object the platform stores.

Each asset has its own AssetIndexAggregate. The aggregate id is derived from the
asset id, so any replica can load the same record from the event store. The index
holds no process-local state.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid5

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.asset import AssetDeleted, AssetUploaded

from runefoble_platform.event_sourcing import AggregateRepository, create_aggregate_repository
from runefoble_platform.storage import AssetNotFoundError

_ASSET_NAMESPACE = uuid5(UUID(int=0), "runefoble.asset-index")


def asset_aggregate_id(asset_id: str) -> UUID:
    """Return the deterministic aggregate id that owns the index record for one asset."""
    return uuid5(_ASSET_NAMESPACE, asset_id)


class AssetIndexState(BaseModel):
    """Projected state for one asset: its stored object metadata, or nothing once deleted."""

    assets: dict[str, dict[str, Any]] = Field(default_factory=dict)


class AssetIndexAggregate(DeclarativeAggregate[AssetIndexState]):
    """Event-sourced index entry for a single Silo asset."""

    aggregate_type = "Asset"
    requires_creation_event = False

    def init_state(self) -> AssetIndexState:
        return AssetIndexState()

    def record_uploaded(self, meta: dict[str, Any]) -> None:
        """Record that Silo confirmed the object write for an asset."""
        self.create_event(
            AssetUploaded,
            aggregate_id=self.aggregate_id,
            asset_id=meta["asset_id"],
            bucket=meta["bucket"],
            object_key=meta["object_key"],
            content_type=meta["content_type"],
            byte_size=meta["byte_size"],
            owner_id=meta["owner_id"],
            url=meta["url"],
        )

    def record_deleted(self, asset_id: str, bucket: str, object_key: str, deleted_by: str) -> None:
        """Record that an asset was removed from Silo."""
        self.create_event(
            AssetDeleted,
            aggregate_id=self.aggregate_id,
            asset_id=asset_id,
            bucket=bucket,
            object_key=object_key,
            deleted_by=deleted_by,
        )

    @handles(AssetUploaded)
    def _on_asset_uploaded(self, event: AssetUploaded) -> None:
        self._ensure_state().assets[event.asset_id] = {
            "asset_id": event.asset_id,
            "bucket": event.bucket,
            "object_key": event.object_key,
            "content_type": event.content_type,
            "byte_size": event.byte_size,
            "owner_id": event.owner_id,
            "url": event.url,
        }

    @handles(AssetDeleted)
    def _on_asset_deleted(self, event: AssetDeleted) -> None:
        self._ensure_state().assets.pop(event.asset_id, None)

    def _ensure_state(self) -> AssetIndexState:
        if self._state is None:
            self._state = self.init_state()
        return self._state


_asset_index_repo: AggregateRepository[AssetIndexAggregate] | None = None


def get_asset_index_repo() -> AggregateRepository[AssetIndexAggregate]:
    """Provide the event-sourced repository behind the asset index."""
    global _asset_index_repo
    if _asset_index_repo is None:
        _asset_index_repo = create_aggregate_repository(AssetIndexAggregate)
    return _asset_index_repo


async def record_stored_asset(meta: dict[str, Any]) -> None:
    """Persist the index entry for an object that Silo has confirmed."""
    repo = get_asset_index_repo()
    aggregate = await repo.load_or_create(asset_aggregate_id(meta["asset_id"]))
    aggregate.record_uploaded(meta)
    await repo.save(aggregate)


async def get_stored_asset(asset_id: str) -> dict[str, Any]:
    """Return the index entry for an asset. Raise AssetNotFoundError if absent or deleted."""
    repo = get_asset_index_repo()
    aggregate = await repo.load_or_create(asset_aggregate_id(asset_id))
    meta = aggregate.state.assets.get(asset_id) if aggregate.version > 0 else None
    if meta is None:
        raise AssetNotFoundError(asset_id)
    return dict(meta)


async def remove_stored_asset(asset_id: str, deleted_by: str) -> dict[str, Any]:
    """Record deletion of an asset and return the entry that was removed."""
    meta = await get_stored_asset(asset_id)
    repo = get_asset_index_repo()
    aggregate = await repo.load(asset_aggregate_id(asset_id))
    aggregate.record_deleted(
        asset_id=asset_id,
        bucket=meta["bucket"],
        object_key=meta["object_key"],
        deleted_by=deleted_by,
    )
    await repo.save(aggregate)
    return meta
