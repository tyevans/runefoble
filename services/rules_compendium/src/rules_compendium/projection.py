"""Start-up rebuild of the homebrew search and lookup index from the event store (ADR-0011).

The event store is the source of truth. The redstring chunks and the per-campaign monster map
are derived state that lives in process memory. This module replays HomebrewRuleRegistered
events into a fresh engine, so homebrew survives a restart. Start-up fails if the store
cannot be read. The service never serves from an empty index.
"""

import logging

from eventsource.ports.store import FullEventStore
from runefoble_events.compendium import HomebrewRuleRegistered

from rules_compendium.aggregate import CompendiumAggregate
from rules_compendium.retrieval import CompendiumRetrievalEngine

logger = logging.getLogger(__name__)


async def rebuild_homebrew_projection(
    engine: CompendiumRetrievalEngine, store: FullEventStore
) -> int:
    """Replay every homebrew rule event into the engine, in stored order. Returns events applied."""
    applied = 0
    async for envelope in store.read_category(CompendiumAggregate.aggregate_type):
        event = envelope.event
        if isinstance(event, HomebrewRuleRegistered):
            await engine.index_homebrew_rule(
                rule_id=event.rule_id,
                campaign_id=event.campaign_id,
                author_id=event.author_id,
                rule_type=event.rule_type,
                title=event.title,
                content=event.content,
            )
            applied += 1
    logger.info("Compendium homebrew projection rebuilt: %d events applied", applied)
    return applied
