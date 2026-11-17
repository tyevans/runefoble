"""Start-up rebuild of the Campaign Lore retrieval projection from the event store.

The event store is the source of truth (ADR-0011). Graph, vector, chunk, and
document metadata are derived state. This module replays LoreDocument events
into a fresh engine so that search and secrecy filtering survive a restart.
"""

import logging

from eventsource.ports.store import FullEventStore
from runefoble_events.events import AliasesConsolidated, LoreDocumentIngested

from campaign_lore.retrieval import LoreRetrievalEngine

logger = logging.getLogger(__name__)

LORE_DOCUMENT_CATEGORY = "LoreDocument"


async def rebuild_lore_projection(engine: LoreRetrievalEngine, store: FullEventStore) -> int:
    """Replay all LoreDocument events into the engine, in stored order. Returns events applied."""
    applied = 0
    async for envelope in store.read_category(LORE_DOCUMENT_CATEGORY):
        event = envelope.event
        if isinstance(event, LoreDocumentIngested):
            await engine.ingest_document(
                document_id=event.document_id,
                campaign_id=event.campaign_id,
                title=event.title,
                content=event.content,
                is_secret=event.is_secret,
            )
            applied += 1
        elif isinstance(event, AliasesConsolidated):
            if event.document_id is None:
                raise RuntimeError(
                    f"AliasesConsolidated for {event.alias_name!r} has no document_id; "
                    "the projection cannot place it"
                )
            await engine.consolidate_alias(
                campaign_id=event.campaign_id,
                canonical_name=event.canonical_name,
                alias_name=event.alias_name,
                document_id=event.document_id,
                reason=event.reason,
            )
            applied += 1
    logger.info("Campaign lore projection rebuilt: %d events applied", applied)
    return applied
