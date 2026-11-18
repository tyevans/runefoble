"""Haven treasury handlers mixin: deposits fund the gold and materials that upgrades spend.

Part of TASK-0786. Governed by ADR-0011 and Hard Invariant 2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eventsource.domain.decorators import handles
from runefoble_events.events import SettlementResourcesDepositedEvent
from runefoble_platform.identifiers import parse_uuid

if TYPE_CHECKING:
    from game_session.settlement.models import SettlementState


class TreasuryHandlersMixin:
    """Event handler and command for the haven gold and material treasury."""

    _state: SettlementState
    aggregate_id: Any
    create_event: Any

    @handles(SettlementResourcesDepositedEvent)
    def handle_resources_deposited(self, ev: SettlementResourcesDepositedEvent) -> None:
        """Add the deposited gold and materials to the treasury."""
        s = self._state
        s.gold_treasury += ev.gold
        for mat, qty in ev.materials.items():
            s.materials_treasury[mat] = s.materials_treasury.get(mat, 0) + qty

    def deposit_resources(
        self,
        gold: int = 0,
        materials: dict[str, int] | None = None,
        deposited_by: str = "",
    ) -> None:
        """Record a deposit of gold and materials into the haven treasury."""
        mats = dict(materials or {})
        if gold < 0 or any(qty < 0 for qty in mats.values()):
            raise ValueError("Deposited gold and materials must not be negative")
        if gold == 0 and not any(mats.values()):
            raise ValueError("Deposit must add gold or materials")
        sid = str(self._state.settlement_id or self.aggregate_id)
        self.create_event(
            SettlementResourcesDepositedEvent,
            aggregate_id=parse_uuid(sid, field="settlement_id"),
            settlement_id=sid,
            shared_world_id=self._state.shared_world_id,
            gold=gold,
            materials=mats,
            deposited_by=deposited_by,
        )
