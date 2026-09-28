"""Domain logic and event-sourced aggregate for merchant haggling interactions.

Part of TASK-0262 / PRD-0024 / US-0075.
Governed by ADR-0001, ADR-0002, ADR-0004, ADR-0006, ADR-0012, and Hard Invariant 2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from game_session.settlement.haggling_models import (
    GambitEvaluationResult,
    NegotiationSession,
    NegotiationSessionState,
)
from game_session.settlement.haggling_valuation import evaluate_gambit
from runefoble_events.haggling import (
    CurrencyCredited,
    CurrencyDeducted,
    DMNegotiationOverridden,
    GambitExecuted,
    NegotiationConcluded,
    NegotiationSessionStarted,
)

__all__ = [
    "NegotiationAggregate",
    "NegotiationSession",
    "NegotiationSessionState",
    "evaluate_gambit",
]


def _to_uuid(val: Any) -> UUID:
    try:
        return val if isinstance(val, UUID) else UUID(str(val))
    except Exception:
        return uuid4()


class NegotiationAggregate(DeclarativeAggregate[NegotiationSessionState]):
    """Event-sourced aggregate managing dynamic bartering and DM arbitration."""

    aggregate_type = "Negotiation"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = NegotiationSessionState(negotiation_id=str(aggregate_id or ""))

    @handles(NegotiationSessionStarted)
    def handle_started(self, ev: NegotiationSessionStarted) -> None:
        self._state.negotiation_id = ev.negotiation_id or str(ev.aggregate_id)
        self._state.session_id = ev.session_id
        self._state.campaign_id = ev.campaign_id
        self._state.establishment_id = ev.establishment_id
        self._state.merchant_id = ev.merchant_id
        self._state.merchant_name = ev.merchant_name
        self._state.character_id = ev.character_id
        self._state.item_id = ev.item_id
        self._state.item_name = ev.item_name
        self._state.original_price = ev.original_price
        self._state.current_offer = ev.current_offer
        self._state.counter_price = ev.counter_price
        self._state.base_margin = ev.base_margin
        self._state.patience = ev.patience
        self._state.temperament = ev.temperament
        self._state.merchant_mood_score = ev.merchant_mood_score
        self._state.status = "active"

    @handles(GambitExecuted)
    def handle_gambit(self, ev: GambitExecuted) -> None:
        self._state.current_offer = ev.new_offer
        self._state.counter_price = ev.counter_price
        self._state.patience = ev.new_patience
        self._state.merchant_mood_score = ev.merchant_mood_score
        self._state.last_bark = ev.voice_bark
        self._state.status = ev.status
        self._state.gambits_history.append(
            {
                "gambit": ev.gambit,
                "roll_value": ev.roll_value,
                "target_dc": ev.target_dc,
                "is_success": ev.is_success,
                "counter_price": ev.counter_price,
                "patience": ev.new_patience,
                "bark": ev.voice_bark,
            }
        )

    @handles(DMNegotiationOverridden)
    def handle_override(self, ev: DMNegotiationOverridden) -> None:
        self._state.patience = ev.new_patience
        self._state.merchant_mood_score = ev.new_mood_score
        if ev.override_price is not None:
            self._state.counter_price = ev.override_price
        if ev.narrative_bark:
            self._state.last_bark = ev.narrative_bark
        self._state.status = ev.status
        self._state.gambits_history.append(
            {
                "dm_override": ev.action,
                "patience": ev.new_patience,
                "mood_score": ev.new_mood_score,
                "bark": ev.narrative_bark,
                "status": ev.status,
            }
        )

    @handles(NegotiationConcluded)
    def handle_concluded(self, ev: NegotiationConcluded) -> None:
        self._state.status = ev.status
        self._state.final_price = ev.final_price
        self._state.last_bark = ev.closing_bark

    @handles(CurrencyDeducted)
    def handle_currency_deducted(self, ev: CurrencyDeducted) -> None:
        pass

    @handles(CurrencyCredited)
    def handle_currency_credited(self, ev: CurrencyCredited) -> None:
        pass

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
        self.create_event(
            NegotiationSessionStarted,
            negotiation_id=str(self.aggregate_id),
            session_id=session_id,
            campaign_id=campaign_id,
            establishment_id=establishment_id,
            merchant_id=merchant_id,
            merchant_name=merchant_name,
            character_id=character_id,
            item_id=item_id,
            item_name=item_name,
            original_price=original_price,
            current_offer=offer,
            counter_price=original_price,
            base_margin=base_margin,
            patience=5,
            temperament=temperament,
            merchant_mood_score=0.0,
            status="active",
        )

    def execute_gambit(
        self,
        character_id: str,
        gambit: str,
        roll_value: int | None = None,
        charisma_mod: int = 0,
        offered_price: int | None = None,
    ) -> GambitEvaluationResult:
        if self._state.status != "active":
            raise ValueError(f"Negotiation is not active (status: {self._state.status})")

        offer = offered_price if offered_price is not None else self._state.current_offer
        result = evaluate_gambit(
            gambit_raw=gambit,
            original_price=self._state.original_price,
            current_offer=offer,
            counter_price=self._state.counter_price,
            temperament_raw=self._state.temperament,
            patience=self._state.patience,
            mood_score=self._state.merchant_mood_score,
            charisma_mod=charisma_mod,
            explicit_roll=roll_value,
        )

        self.create_event(
            GambitExecuted,
            negotiation_id=str(self.aggregate_id),
            character_id=character_id,
            gambit=result.gambit.value,
            roll_value=result.roll_value,
            target_dc=result.target_dc,
            is_success=result.is_success,
            price_delta=result.price_delta,
            new_offer=result.new_offer,
            counter_price=result.counter_price,
            patience_delta=result.patience_delta,
            new_patience=result.new_patience,
            mood_delta=result.mood_delta,
            merchant_mood_score=result.new_mood_score,
            voice_bark=result.voice_bark,
            status=result.status,
        )

        if result.status == "completed":
            self.create_event(
                NegotiationConcluded,
                negotiation_id=str(self.aggregate_id),
                session_id=self._state.session_id,
                campaign_id=self._state.campaign_id,
                establishment_id=self._state.establishment_id,
                character_id=character_id,
                merchant_id=self._state.merchant_id,
                item_id=self._state.item_id,
                item_name=self._state.item_name,
                final_price=result.new_offer,
                status="completed",
                currency_deducted=result.new_offer,
                inventory_item_credited=self._state.item_id,
                closing_bark=result.voice_bark,
            )
            self.create_event(
                CurrencyDeducted,
                character_id=character_id,
                amount=result.new_offer,
                currency="gp",
                reason="merchant_haggling_purchase",
                session_id=self._state.session_id,
                campaign_id=self._state.campaign_id,
            )
        elif result.status == "refused":
            self.create_event(
                NegotiationConcluded,
                negotiation_id=str(self.aggregate_id),
                session_id=self._state.session_id,
                campaign_id=self._state.campaign_id,
                establishment_id=self._state.establishment_id,
                character_id=character_id,
                merchant_id=self._state.merchant_id,
                item_id=self._state.item_id,
                item_name=self._state.item_name,
                final_price=0,
                status="refused",
                currency_deducted=0,
                inventory_item_credited="",
                closing_bark=result.voice_bark,
            )

        return result

    def dm_override(
        self,
        dm_user_id: str,
        action: str,
        override_price_gp: int | None = None,
        narrative_bark: str | None = None,
        patience_delta: int = 0,
        mood_delta: float = 0.0,
    ) -> None:
        if self._state.status in ("completed", "refused", "terminated"):
            raise ValueError(f"Negotiation already closed (status: {self._state.status})")

        act = action.lower().strip()
        new_p = self._state.patience
        new_m = self._state.merchant_mood_score
        new_status = "active"
        target_price = override_price_gp or self._state.counter_price
        bark = narrative_bark or ""

        if act in ("soothe_merchant", "soothe"):
            new_p = min(5, self._state.patience + (patience_delta or 2))
            new_m = min(50.0, self._state.merchant_mood_score + (mood_delta or 15.0))
            bark = bark or "The merchant breathes calmly, settling down with relaxed shoulders."
        elif act in ("enrage_merchant", "enrage"):
            new_p = max(0, self._state.patience + (patience_delta or -2))
            new_m = max(-50.0, self._state.merchant_mood_score + (mood_delta or -20.0))
            bark = bark or "The merchant scowls with red-faced irritation!"
            if new_p <= 0:
                new_status = "refused"
        elif act in ("accept_deal", "force_accept", "accept"):
            new_status = "completed"
            target_price = override_price_gp or self._state.current_offer
            bark = bark or "The DM signals approval. The merchant nods and seals the trade."
        elif act in ("refuse_kick_out", "refuse", "kick_out", "terminate"):
            new_status = "terminated"
            bark = bark or "The deal collapses entirely. The merchant motions to the door."
        elif act in ("override_price", "set_price"):
            target_price = (
                override_price_gp if override_price_gp is not None else self._state.counter_price
            )
            bark = bark or f"Price adjusted to {target_price} gold."
        elif act in ("inject_bark", "bark"):
            bark = bark or "The merchant grunts thoughtfully."

        self.create_event(
            DMNegotiationOverridden,
            negotiation_id=str(self.aggregate_id),
            dm_user_id=dm_user_id,
            action=act,
            patience_delta=patience_delta,
            new_patience=new_p,
            mood_delta=mood_delta,
            new_mood_score=new_m,
            override_price=target_price,
            narrative_bark=bark,
            status=new_status,
        )

        if new_status == "completed":
            self.create_event(
                NegotiationConcluded,
                negotiation_id=str(self.aggregate_id),
                session_id=self._state.session_id,
                campaign_id=self._state.campaign_id,
                establishment_id=self._state.establishment_id,
                character_id=self._state.character_id,
                merchant_id=self._state.merchant_id,
                item_id=self._state.item_id,
                item_name=self._state.item_name,
                final_price=target_price,
                status="completed",
                currency_deducted=target_price,
                inventory_item_credited=self._state.item_id,
                closing_bark=bark,
            )
            self.create_event(
                CurrencyDeducted,
                character_id=self._state.character_id,
                amount=target_price,
                currency="gp",
                reason="merchant_haggling_dm_override",
                session_id=self._state.session_id,
                campaign_id=self._state.campaign_id,
            )
        elif new_status in ("refused", "terminated"):
            self.create_event(
                NegotiationConcluded,
                negotiation_id=str(self.aggregate_id),
                session_id=self._state.session_id,
                campaign_id=self._state.campaign_id,
                establishment_id=self._state.establishment_id,
                character_id=self._state.character_id,
                merchant_id=self._state.merchant_id,
                item_id=self._state.item_id,
                item_name=self._state.item_name,
                final_price=0,
                status=new_status,
                currency_deducted=0,
                inventory_item_credited="",
                closing_bark=bark,
            )
