"""Event-sourced Settlement Aggregate facade for backwards compatibility.

Governed by ADR-0007, ADR-0011, and Hard Invariant 2.
"""

from __future__ import annotations

from game_session.settlement.settlement_aggregate import (
    SettlementAggregate,
    _to_uuid,
)

__all__ = ["SettlementAggregate", "_to_uuid"]
