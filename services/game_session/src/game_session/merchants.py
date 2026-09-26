"""Merchant Haggling and Personality-Driven Temperament System.

Governed by Hard Invariant 2: Domain state transitions flow strictly through
DeclarativeAggregate subclasses with @handles methods.
Part of TASK-0103 / PRD-0014 / US-0047.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from game_session.minigame_rules import to_opt_uuid, to_uuid
from pydantic import BaseModel, Field
from runefoble_events.tavern import HagglingNegotiated

MERCHANT_TEMPERAMENTS: dict[str, dict[str, Any]] = {
    "stubborn_greedy": {
        "min_acceptable_ratio": 0.92,
        "counter_weight": 0.47,
        "mood_resilience": 1.2,
        "default_name": "Thorin Stoneforged (Dwarven Blacksmith)",
    },
    "shrewd": {
        "min_acceptable_ratio": 0.88,
        "counter_weight": 0.50,
        "mood_resilience": 1.0,
        "default_name": "Valen the Ledger-Keeper",
    },
    "generous": {
        "min_acceptable_ratio": 0.70,
        "counter_weight": 0.30,
        "mood_resilience": 0.8,
        "default_name": "Milo Goodbarrel",
    },
    "hostile": {
        "min_acceptable_ratio": 0.95,
        "counter_weight": 0.80,
        "mood_resilience": 1.5,
        "default_name": "Krag the Smuggler",
    },
    "gullible": {
        "min_acceptable_ratio": 0.65,
        "counter_weight": 0.20,
        "mood_resilience": 0.5,
        "default_name": "Barnaby the Apprentice",
    },
}


def calculate_haggling_outcome(
    base_price: int,
    offered_price: int,
    temperament: str,
    mood_score: float,
    charisma_modifier: int,
    dialogue: str = "",
) -> tuple[str, int | None, float, str]:
    """Calculate negotiation outcome, counter-offer, mood shift, and merchant voice line."""
    temp_config = MERCHANT_TEMPERAMENTS.get(temperament, MERCHANT_TEMPERAMENTS["stubborn_greedy"])
    raw_ratio = offered_price / max(1, base_price)
    charisma_bonus = (charisma_modifier * 0.05) + (mood_score * 0.002)
    effective_ratio = raw_ratio + charisma_bonus

    if effective_ratio >= 0.95:
        outcome = "accepted"
        agreed_price = offered_price
        new_mood = min(50.0, mood_score + 10.0)
        bark = f"Deal! Take the item for {agreed_price} gold. Pleasure doing business!"
    elif raw_ratio < (temp_config["min_acceptable_ratio"] - 0.25):
        outcome = "insulted"
        agreed_price = None
        new_mood = max(-50.0, mood_score - 15.0)
        bark = "Do ye mistake me for a beggar? Get out of me sight with that insult of an offer!"
    elif effective_ratio >= temp_config["min_acceptable_ratio"]:
        outcome = "accepted"
        agreed_price = offered_price
        new_mood = min(50.0, mood_score + 5.0)
        bark = f"You make a compelling argument. Sold for {agreed_price} gold!"
    else:
        outcome = "countered"
        c_weight = temp_config["counter_weight"]
        counter = round(offered_price + (base_price - offered_price) * c_weight)
        counter = min(base_price, max(offered_price + 1, counter))
        agreed_price = counter
        new_mood = max(-50.0, min(50.0, mood_score + charisma_modifier * 2))
        if temperament == "stubborn_greedy":
            bark = f"Dwarven steel doesn't bend for pennies! Meet me at {counter} gold, or keep walkin'!"
        else:
            bark = (
                f"I cannot accept {offered_price} gold, but I can part with it for {counter} gold."
            )

    return outcome, agreed_price, new_mood, bark


class MerchantState(BaseModel):
    """Event-sourced merchant state tracking mood and negotiation history."""

    merchant_id: str = ""
    name: str = "Merchant"
    temperament: str = "stubborn_greedy"
    mood_score: float = 0.0
    total_negotiations: int = 0
    successful_deals: int = 0
    history: list[dict[str, Any]] = Field(default_factory=list)


class MerchantAggregate(DeclarativeAggregate[MerchantState]):
    """Event-sourced aggregate managing NPC merchant temperaments, bartering, and dialogue."""

    aggregate_type = "Merchant"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        agg_uuid = to_uuid(aggregate_id) if aggregate_id else uuid4()
        super().__init__(aggregate_id=agg_uuid, **kwargs)
        if self._state is None:
            self._state = MerchantState(merchant_id=str(aggregate_id or agg_uuid))

    @handles(HagglingNegotiated)
    def handle_negotiated(self, event: HagglingNegotiated) -> None:
        self.state.merchant_id = event.merchant_id
        self.state.temperament = event.merchant_mood
        self.state.mood_score = event.mood_score
        self.state.total_negotiations += 1
        if event.outcome in ("accepted", "countered"):
            self.state.successful_deals += 1
        self.state.history.append(
            {
                "item_name": event.item_name,
                "base_price": event.base_price,
                "offered_price": event.offered_price,
                "outcome": event.outcome,
                "agreed_price": event.agreed_price,
                "voice_bark": event.voice_bark,
            }
        )

    def negotiate(
        self,
        character_id: str,
        item_name: str,
        base_price: int,
        offered_price: int,
        charisma_modifier: int = 0,
        dialogue: str = "",
        session_id: str | None = None,
        campaign_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute a social bartering interaction, updating mood and price curve."""
        outcome, price, new_mood, bark = calculate_haggling_outcome(
            base_price=base_price,
            offered_price=offered_price,
            temperament=self.state.temperament,
            mood_score=self.state.mood_score,
            charisma_modifier=charisma_modifier,
            dialogue=dialogue,
        )

        counter_price = price if outcome == "countered" else None
        agreed_price = price if outcome in ("accepted", "countered") else None

        self.create_event(
            HagglingNegotiated,
            merchant_id=self.state.merchant_id,
            session_id=to_opt_uuid(session_id),
            campaign_id=to_opt_uuid(campaign_id),
            character_id=character_id,
            item_name=item_name,
            base_price=base_price,
            offered_price=offered_price,
            counter_price=counter_price,
            agreed_price=agreed_price,
            merchant_mood=self.state.temperament,
            mood_score=new_mood,
            outcome=outcome,
            dialogue=dialogue,
            voice_bark=bark,
        )

        return {
            "merchant_id": self.state.merchant_id,
            "temperament": self.state.temperament,
            "outcome": outcome,
            "base_price": base_price,
            "offered_price": offered_price,
            "counter_price": counter_price,
            "agreed_price": agreed_price,
            "mood_score": new_mood,
            "voice_bark": bark,
        }


__all__ = [
    "MERCHANT_TEMPERAMENTS",
    "MerchantAggregate",
    "MerchantState",
    "calculate_haggling_outcome",
    "to_opt_uuid",
    "to_uuid",
]
