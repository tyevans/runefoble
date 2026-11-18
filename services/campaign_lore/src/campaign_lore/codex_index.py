"""Campaign codex entry list, read from the Codex event stream.

The event store is the source of truth (ADR-0011, ADR-0015). A codex entry exists when its
`CodexEntryPublished` event is committed. The list is read from those events on each
request, so it does not depend on the state of any one process.
"""

from __future__ import annotations

from uuid import UUID

from eventsource.ports.store import FullEventStore
from runefoble_events.lore import CodexEntryPublished

CODEX_CATEGORY = "Codex"


async def campaign_codex_entry_ids(store: FullEventStore, campaign_id: UUID) -> list[UUID]:
    """Return the ids of the campaign's codex entries, in the order they were published."""
    entry_ids: dict[UUID, None] = {}
    async for envelope in store.read_category(CODEX_CATEGORY):
        event = envelope.event
        if isinstance(event, CodexEntryPublished) and event.campaign_id == campaign_id:
            entry_ids.setdefault(event.entry_id, None)
    return list(entry_ids)
