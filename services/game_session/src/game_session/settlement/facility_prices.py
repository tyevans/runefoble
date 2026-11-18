"""Tier price table for settlement and haven facility upgrades.

Each upgrade spends the listed gold and materials from the haven treasury (TASK-0786).
Prices are modest defaults. Operators tune them here, then update the how-to guide.
Governed by ADR-0011 and Hard Invariant 2.
"""

from __future__ import annotations

from typing import Any

SETTLEMENT_FACILITY_PRICES: dict[str, dict[int, dict[str, Any]]] = {
    "workshop": {
        1: {"cost_gold": 50, "cost_materials": {"timber": 10}},
        2: {"cost_gold": 100, "cost_materials": {"timber": 20}},
        3: {"cost_gold": 250, "cost_materials": {"timber": 30, "stone": 40}},
    },
    "sanctum": {
        1: {"cost_gold": 60, "cost_materials": {"timber": 10}},
        2: {"cost_gold": 120, "cost_materials": {"timber": 20}},
        3: {"cost_gold": 280, "cost_materials": {"timber": 30, "stone": 40}},
    },
    "fortifications": {
        1: {"cost_gold": 60, "cost_materials": {"stone": 15}},
        2: {"cost_gold": 150, "cost_materials": {"stone": 30}},
        3: {"cost_gold": 350, "cost_materials": {"stone": 60, "iron": 20}},
    },
    "watchtower": {
        1: {"cost_gold": 40, "cost_materials": {"timber": 10}},
        2: {"cost_gold": 90, "cost_materials": {"timber": 20}},
        3: {"cost_gold": 220, "cost_materials": {"timber": 25, "stone": 30}},
    },
    "trading_post": {
        1: {"cost_gold": 75, "cost_materials": {"timber": 15}},
        2: {"cost_gold": 150, "cost_materials": {"timber": 25, "stone": 10}},
        3: {"cost_gold": 320, "cost_materials": {"timber": 40, "stone": 40}},
    },
}

MAX_FACILITY_TIER = 3


class InsufficientSettlementResources(ValueError):
    """Raised when the haven treasury cannot pay the tier price. Answers 409."""


def treasury_shortfalls(
    held_gold: int,
    held_materials: dict[str, int],
    gold: int,
    materials: dict[str, int],
) -> list[str]:
    """Describe each gold or material amount that the haven treasury cannot cover."""
    problems: list[str] = []
    if gold > held_gold:
        problems.append(f"gold: need {gold}, treasury holds {held_gold}")
    for mat, qty in materials.items():
        held = held_materials.get(mat, 0)
        if qty > held:
            problems.append(f"{mat}: need {qty}, treasury holds {held}")
    return problems


__all__ = [
    "MAX_FACILITY_TIER",
    "SETTLEMENT_FACILITY_PRICES",
    "InsufficientSettlementResources",
    "treasury_shortfalls",
]
