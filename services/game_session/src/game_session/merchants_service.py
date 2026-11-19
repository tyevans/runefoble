"""Merchant application service: load or create, negotiate, save, and publish.

Routers call these functions and map the typed results to HTTP. Routers never load, mutate,
or save a MerchantAggregate themselves (ADR-0015, Hard Invariant 2). A store error propagates
unchanged and maps to HTTP 503. Only a missing stream is treated as absence (TASK-0561).
Part of TASK-0728 / PRD-0024 / US-0047.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from game_session.dependencies import get_event_bus, get_merchant_repository
from game_session.merchants import MerchantAggregate
from game_session.shared.streams import STREAM_TAVERN
from runefoble_platform.aggregate_loading import load_if_exists, load_or_create
from runefoble_platform.event_publish import publish_aggregate_events
from runefoble_platform.identifiers import opaque_aggregate_id


@dataclass(frozen=True)
class HaggleOffer:
    """One offer that a character makes to a merchant for an item."""

    character_id: str
    item_name: str
    base_price: int
    offered_price: int
    charisma_modifier: int = 0
    dialogue: str = ""


@dataclass(frozen=True)
class HaggleResult:
    """The merchant's answer to one offer."""

    temperament: str
    outcome: str
    base_price: int
    offered_price: int
    counter_price: int | None
    agreed_price: int | None
    mood_score: float
    voice_bark: str | None


async def haggle(
    *,
    merchant_id: str,
    session_id: str,
    temperament: str,
    offer: HaggleOffer,
) -> HaggleResult:
    """Negotiate an offer. A merchant that has no stream yet is recorded first.

    The creation event, when there is one, precedes the negotiation event in the stream.
    """
    repo = get_merchant_repository()
    aggregate = await load_or_create(
        repo,
        opaque_aggregate_id(merchant_id, field="merchant_id"),
        lambda agg_id: MerchantAggregate.create(agg_id, merchant_id, temperament),
    )

    res = aggregate.negotiate(
        character_id=offer.character_id,
        item_name=offer.item_name,
        base_price=offer.base_price,
        offered_price=offer.offered_price,
        charisma_modifier=offer.charisma_modifier,
        dialogue=offer.dialogue,
        session_id=session_id,
    )

    events_to_publish = list(aggregate.uncommitted_events)
    await repo.save(aggregate)

    bus = get_event_bus()
    if bus:
        await publish_aggregate_events(bus, STREAM_TAVERN, events_to_publish)

    return HaggleResult(
        temperament=res["temperament"],
        outcome=res["outcome"],
        base_price=res["base_price"],
        offered_price=res["offered_price"],
        counter_price=res["counter_price"],
        agreed_price=res["agreed_price"],
        mood_score=res["mood_score"],
        voice_bark=res["voice_bark"],
    )


async def load_merchant_profile(merchant_id: str) -> dict[str, Any] | None:
    """Return the merchant state, or None when no merchant stream exists for the id."""
    aggregate = await load_if_exists(
        get_merchant_repository(), opaque_aggregate_id(merchant_id, field="merchant_id")
    )
    if aggregate is None:
        return None
    data = aggregate.state.model_dump()
    data["merchant_id"] = merchant_id
    return data


__all__ = [
    "HaggleOffer",
    "HaggleResult",
    "haggle",
    "load_merchant_profile",
]
