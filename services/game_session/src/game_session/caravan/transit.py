"""Transit stage calculations, hazard progression, and contract payout validation.

Part of TASK-0186 / PRD-0007 / US-0058 / ADR-0007.
"""

from __future__ import annotations

from typing import Any


def validate_contract_post(
    origin_outpost: str,
    destination_outpost: str,
    cargo: dict[str, int],
    cargo_value: int,
) -> None:
    """Validate posting parameters for a caravan mercenary contract."""
    if origin_outpost.strip().lower() == destination_outpost.strip().lower():
        raise ValueError("Origin and destination outposts must be distinct")
    if not cargo or sum(cargo.values()) <= 0:
        raise ValueError("Caravan cargo manifest must contain at least one item")
    if cargo_value <= 0:
        raise ValueError("Cargo value must be greater than zero")


def validate_can_accept(status: str) -> None:
    """Validate contract status before mercenary acceptance."""
    if status != "open":
        raise ValueError(f"Cannot accept contract with status '{status}'")


def validate_can_dispatch(status: str) -> None:
    """Validate contract status before caravan dispatch."""
    if status != "accepted":
        raise ValueError(f"Cannot dispatch caravan for contract with status '{status}'")


def validate_ambush_outcome(status: str, outcome: str) -> None:
    """Validate ambush conditions and tactical outcome string."""
    if status not in ("in_transit", "ambushed"):
        raise ValueError(f"Cannot report ambush for contract with status '{status}'")
    if outcome not in ("repelled", "cargo_damaged", "caravan_destroyed"):
        raise ValueError(f"Invalid ambush outcome: '{outcome}'")


def validate_can_fulfill(status: str) -> None:
    """Validate contract status before cargo fulfillment."""
    if status not in ("in_transit", "ambushed"):
        raise ValueError(f"Cannot fulfill contract with status '{status}' (must be in transit)")


def calculate_transit_ambush_progress(
    current_stage: int,
    transit_stages: int,
    stage_index: int,
    outcome: str,
    current_loss_pct: float,
    reported_loss_pct: float,
) -> tuple[str, int, float]:
    """Calculate updated contract status, transit stage, and cargo loss percentage."""
    if outcome == "caravan_destroyed":
        return "failed", current_stage, 1.0
    if outcome == "cargo_damaged":
        new_loss = min(1.0, current_loss_pct + reported_loss_pct)
        next_stage = min(transit_stages, stage_index + 1)
        return "in_transit", next_stage, new_loss
    # Repelled
    next_stage = min(transit_stages, stage_index + 1)
    return "in_transit", next_stage, current_loss_pct


def calculate_contract_payout(
    cargo: dict[str, int],
    cargo_value: int,
    reward_gold: int,
    escort_collateral: int,
    reward_reputation: int,
    cargo_loss_percentage: float,
) -> dict[str, Any]:
    """Calculate surviving delivered cargo, delivered cargo value, and escort escrow payout."""
    loss = min(1.0, max(0.0, cargo_loss_percentage))
    surviving_ratio = 1.0 - loss

    delivered_cargo = {
        item: max(0, int(round(qty * surviving_ratio))) for item, qty in cargo.items()
    }
    cargo_value_delivered = int(round(cargo_value * surviving_ratio))
    gold_payout = int(round(reward_gold * (1.0 - (loss * 0.5)))) + escort_collateral
    reputation = max(1, int(round(reward_reputation * surviving_ratio)))

    return {
        "cargo_delivered": delivered_cargo,
        "cargo_value_delivered": cargo_value_delivered,
        "reward_gold_paid": gold_payout,
        "reputation_awarded": reputation,
    }


__all__ = [
    "calculate_contract_payout",
    "calculate_transit_ambush_progress",
    "validate_ambush_outcome",
    "validate_can_accept",
    "validate_can_dispatch",
    "validate_can_fulfill",
    "validate_contract_post",
]
