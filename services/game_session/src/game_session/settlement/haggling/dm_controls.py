"""DM arbitration and live veto controls for merchant haggling.

Governed by ADR-0002, ADR-0007, ADR-0013, and Hard Invariant 2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eventsource.domain.decorators import handles
from runefoble_events.haggling import DMNegotiationOverridden

if TYPE_CHECKING:
    from game_session.settlement.haggling_models import NegotiationSessionState

__all__ = ["DMControlsMixin"]


class DMControlsMixin:
    """DM intervention handlers, manual price overrides, dialogue injections, and deal approval."""

    _state: NegotiationSessionState
    aggregate_id: Any
    create_event: Any
    _conclude_negotiation: Any

    @handles(DMNegotiationOverridden)
    def handle_override(self, ev: DMNegotiationOverridden) -> None:
        s = self._state
        s.patience, s.merchant_mood_score = ev.new_patience, ev.new_mood_score
        if ev.override_price is not None:
            s.counter_price = ev.override_price
        s.last_bark, s.status = ev.narrative_bark or s.last_bark, ev.status
        s.gambits_history.append(
            {
                "dm_override": ev.action,
                "patience": ev.new_patience,
                "mood_score": ev.new_mood_score,
                "bark": ev.narrative_bark,
                "status": ev.status,
            }
        )

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
        s = self._state
        new_p, new_m = s.patience, s.merchant_mood_score
        new_status, bark = "active", narrative_bark or ""
        target_price = override_price_gp or s.counter_price

        if act in ("soothe_merchant", "soothe"):
            new_p = min(5, new_p + (patience_delta or 2))
            new_m = min(50.0, new_m + (mood_delta or 15.0))
            bark = bark or "The merchant breathes calmly, settling down with relaxed shoulders."
        elif act in ("enrage_merchant", "enrage"):
            new_p = max(0, new_p + (patience_delta or -2))
            new_m = max(-50.0, new_m + (mood_delta or -20.0))
            bark = bark or "The merchant scowls with red-faced irritation!"
            new_status = "refused" if new_p <= 0 else new_status
        elif act in ("accept_deal", "force_accept", "accept"):
            new_status, target_price = "completed", override_price_gp or s.current_offer
            bark = bark or "The DM signals approval. The merchant nods and seals the trade."
        elif act in ("refuse_kick_out", "refuse", "kick_out", "terminate"):
            new_status = "terminated"
            bark = bark or "The deal collapses entirely. The merchant motions to the door."
        elif act in ("override_price", "set_price"):
            target_price = override_price_gp if override_price_gp is not None else s.counter_price
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

        if new_status in ("completed", "refused", "terminated"):
            self._conclude_negotiation(
                s.character_id, new_status, target_price, bark, "merchant_haggling_dm_override"
            )
