"""Rhetoric moves, player bartering actions, and temperament modifiers.

Governed by ADR-0002, ADR-0007, ADR-0013, and Hard Invariant 2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eventsource.domain.decorators import handles
from game_session.settlement.haggling_models import GambitEvaluationResult
from game_session.settlement.haggling_valuation import evaluate_gambit
from runefoble_events.haggling import GambitExecuted

if TYPE_CHECKING:
    from game_session.settlement.haggling_models import NegotiationSessionState

__all__ = ["RhetoricMovesMixin"]


class RhetoricMovesMixin:
    """Player bartering moves, skill check formulas, and merchant reaction formulas."""

    _state: NegotiationSessionState
    aggregate_id: Any
    create_event: Any
    _conclude_negotiation: Any

    @handles(GambitExecuted)
    def handle_gambit(self, ev: GambitExecuted) -> None:
        s = self._state
        s.current_offer, s.counter_price = ev.new_offer, ev.counter_price
        s.patience, s.merchant_mood_score = ev.new_patience, ev.merchant_mood_score
        s.last_bark, s.status = ev.voice_bark, ev.status
        s.gambits_history.append(
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

        if result.status in ("completed", "refused"):
            self._conclude_negotiation(
                character_id=character_id,
                status=result.status,
                final_price=result.new_offer,
                closing_bark=result.voice_bark,
                reason="merchant_haggling_purchase",
            )

        return result
