"""Haggling session state machine and event-sourced aggregate.

Governed by ADR-0002, ADR-0007, ADR-0013, and Hard Invariant 2.
"""

from __future__ import annotations

from typing import Any

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from game_session.settlement.haggling.dm_controls import DMControlsMixin
from game_session.settlement.haggling.rhetoric import RhetoricMovesMixin
from game_session.settlement.haggling_models import NegotiationSession, NegotiationSessionState
from runefoble_events.haggling import (
    CurrencyCredited,
    CurrencyDeducted,
    NegotiationConcluded,
    NegotiationSessionStarted,
)

__all__ = ["NegotiationAggregate", "NegotiationSession", "NegotiationSessionState"]


class NegotiationAggregate(
    RhetoricMovesMixin, DMControlsMixin, DeclarativeAggregate[NegotiationSessionState]
):
    """Event-sourced aggregate managing dynamic bartering and DM arbitration."""

    aggregate_type = "Negotiation"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = NegotiationSessionState(negotiation_id=str(aggregate_id or ""))

    @handles(NegotiationSessionStarted)
    def handle_started(self, ev: NegotiationSessionStarted) -> None:
        s = self._state
        s.negotiation_id = ev.negotiation_id or str(ev.aggregate_id)
        s.session_id, s.campaign_id = ev.session_id, ev.campaign_id
        s.establishment_id = ev.establishment_id
        s.merchant_id, s.merchant_name = ev.merchant_id, ev.merchant_name
        s.character_id, s.item_id, s.item_name = ev.character_id, ev.item_id, ev.item_name
        s.original_price, s.current_offer = ev.original_price, ev.current_offer
        s.counter_price, s.base_margin = ev.counter_price, ev.base_margin
        s.patience, s.temperament = ev.patience, ev.temperament
        s.merchant_mood_score, s.status = ev.merchant_mood_score, "active"

    @handles(NegotiationConcluded)
    def handle_concluded(self, ev: NegotiationConcluded) -> None:
        s = self._state
        s.status, s.final_price, s.last_bark = ev.status, ev.final_price, ev.closing_bark

    @handles(CurrencyDeducted)
    def handle_currency_deducted(self, ev: CurrencyDeducted) -> None: ...

    @handles(CurrencyCredited)
    def handle_currency_credited(self, ev: CurrencyCredited) -> None: ...

    def _conclude_negotiation(
        self, character_id: str, status: str, final_price: int, closing_bark: str, reason: str
    ) -> None:
        is_done, s = status == "completed", self._state
        p = final_price if is_done else 0
        kw = {"negotiation_id": str(self.aggregate_id), "character_id": character_id}
        kw.update(
            session_id=s.session_id, campaign_id=s.campaign_id, establishment_id=s.establishment_id
        )
        kw.update(merchant_id=s.merchant_id, item_id=s.item_id, item_name=s.item_name)
        kw.update(final_price=p, status=status, currency_deducted=p, closing_bark=closing_bark)
        kw.update(inventory_item_credited=s.item_id if is_done else "")
        self.create_event(NegotiationConcluded, **kw)
        if is_done:
            ded = {"character_id": character_id, "amount": p, "currency": "gp", "reason": reason}
            ded.update(session_id=s.session_id, campaign_id=s.campaign_id)
            self.create_event(CurrencyDeducted, **ded)

    def start_negotiation(
        self,
        character_id: str,
        item_id: str,
        item_name: str,
        original_price: int,
        initial_offer_gp: int | None = None,
        establishment_id: str = "",
        merchant_id: str = "",
        merchant_name: str = "Merchant",
        campaign_id: str = "",
        session_id: str = "",
        temperament: str = "Stubborn",
        base_margin: float = 0.20,
    ) -> None:
        if self._state.status == "completed":
            raise ValueError("Negotiation already completed")
        offer = initial_offer_gp if initial_offer_gp is not None else int(original_price * 0.8)
        kw = {"negotiation_id": str(self.aggregate_id), "character_id": character_id}
        kw.update(item_id=item_id, item_name=item_name, original_price=original_price)
        kw.update(current_offer=offer, counter_price=original_price, base_margin=base_margin)
        kw.update(patience=5, temperament=temperament, merchant_mood_score=0.0, status="active")
        kw.update(session_id=session_id, campaign_id=campaign_id)
        kw.update(
            establishment_id=establishment_id, merchant_id=merchant_id, merchant_name=merchant_name
        )
        self.create_event(NegotiationSessionStarted, **kw)
