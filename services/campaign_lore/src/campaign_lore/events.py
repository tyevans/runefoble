"""Stream names and the lore event-to-stream mapping for the Campaign Lore repositories.

Every event that a lore aggregate commits is published by its repository. The table below
is the only place that chooses the stream for a lore event. An unmapped event fails the
save, so a new event cannot be committed without a stream.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from eventsource.domain.event import DomainEvent
from runefoble_events.lore import (
    AliasesConsolidated,
    AtlasLayerToggled,
    AtlasPinCreated,
    AtlasTerritoryUpdated,
    CodexEntryPublished,
    CodexEntryUpdated,
    EntitiesExtracted,
    HandoutGenerated,
    InvisibleInkRevealed,
    LoreDocumentIngested,
    RelicForged,
    RelicInspected,
    RelicRuneTranslated,
    WaxSealBroken,
)
from runefoble_events.west_marches import (
    CampaignRegisteredToSharedWorld,
    CommunalNoticePosted,
    CrossCampaignDiscoveryShared,
    OutpostEstablished,
    OutpostResourcesContributed,
    SharedStrongholdUpgraded,
    SharedWorldCreated,
)
from runefoble_platform.event_publish import publish_or_fail

LORE_EVENT_STREAMS: dict[type[DomainEvent], str] = {
    LoreDocumentIngested: "runefoble.events.lore.document_ingested",
    EntitiesExtracted: "runefoble.events.lore.entities_extracted",
    AliasesConsolidated: "runefoble.events.lore.aliases_consolidated",
    HandoutGenerated: "runefoble.events.lore.handout_generated",
    WaxSealBroken: "runefoble.events.lore.wax_seal_broken",
    InvisibleInkRevealed: "runefoble.events.lore.invisible_ink_revealed",
    RelicForged: "runefoble.events.lore.relic_forged",
    RelicInspected: "runefoble.events.lore.relic_inspected",
    RelicRuneTranslated: "runefoble.events.lore.relic_rune_translated",
    AtlasPinCreated: "runefoble.events.lore.atlas_pin_created",
    AtlasLayerToggled: "runefoble.events.lore.atlas_layer_toggled",
    AtlasTerritoryUpdated: "runefoble.events.lore.atlas_territory_updated",
    CodexEntryPublished: "runefoble.events.lore.codex_entry_published",
    CodexEntryUpdated: "runefoble.events.lore.codex_entry_updated",
    SharedWorldCreated: "runefoble.events.lore.shared_world_created",
    CampaignRegisteredToSharedWorld: "runefoble.events.lore.campaign_registered_to_shared_world",
    CrossCampaignDiscoveryShared: "runefoble.events.lore.cross_campaign_discovery_shared",
    OutpostEstablished: "runefoble.events.lore.outpost_established",
    OutpostResourcesContributed: "runefoble.events.lore.outpost_resources_contributed",
    SharedStrongholdUpgraded: "runefoble.events.lore.shared_stronghold_upgraded",
    CommunalNoticePosted: "runefoble.events.lore.communal_notice_posted",
}


class UnmappedLoreEventError(RuntimeError):
    """Raised when a lore repository commits an event family with no stream mapping."""


def stream_for_lore_event(event: DomainEvent) -> str:
    """Return the stream that a committed lore event is published to."""
    try:
        return LORE_EVENT_STREAMS[type(event)]
    except KeyError as exc:
        raise UnmappedLoreEventError(
            f"No stream mapping for lore event '{type(event).__name__}'"
        ) from exc


class LoreEventPublisher:
    """Publishes each committed lore event to its mapped stream through the repository.

    The bus is resolved on each call. A publish failure raises DomainEventPublishError,
    which the API maps to HTTP 503.
    """

    def __init__(self, bus_provider: Callable[[], Any]) -> None:
        self._bus_provider = bus_provider

    async def publish(self, events: Sequence[DomainEvent]) -> None:
        bus = self._bus_provider()
        for event in events:
            await publish_or_fail(bus, stream_for_lore_event(event), event)
