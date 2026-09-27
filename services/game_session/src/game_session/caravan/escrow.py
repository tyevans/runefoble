"""Escrow validation, economic pricing modifiers, and regional stock accounting.

Part of TASK-0186 / PRD-0007 / US-0058 / ADR-0007.
"""

from __future__ import annotations

from typing import Any


def calculate_economic_price_modifier(total_deliveries: int, successful_deliveries: int) -> float:
    """Calculate economic price modifier based on caravan delivery success rate.

    - 100% safe deliveries (high supply / trade route secured) -> 0.90 (abundance discount).
    - 100% baseline with low deliveries -> 1.00.
    - Low delivery success rate (scarcity due to ambushes) -> up to 1.50 (scarcity surcharge).
    """
    if total_deliveries <= 0:
        return 1.0
    success_rate = successful_deliveries / total_deliveries
    if success_rate >= 0.99 and total_deliveries >= 2:
        return 0.90
    modifier = 1.0 + (1.0 - success_rate) * 0.50
    return round(max(0.80, min(1.60, modifier)), 2)


def ensure_outpost_stock_entry(stocks: dict[str, dict[str, Any]], dest: str) -> dict[str, Any]:
    """Ensure outpost stock entry exists with proper initialized structure."""
    dest_key = dest.lower()
    if dest_key not in stocks:
        stocks[dest_key] = {
            "inventory": {},
            "workshop_reagents": {},
            "delivery_stats": {
                "total_deliveries": 0,
                "successful_deliveries": 0,
                "ambushed_deliveries": 0,
                "success_rate": 1.0,
            },
            "price_modifier": 1.0,
            "last_delivery": None,
        }
    elif "delivery_stats" not in stocks[dest_key]:
        stocks[dest_key]["delivery_stats"] = {
            "total_deliveries": 0,
            "successful_deliveries": 0,
            "ambushed_deliveries": 0,
            "success_rate": 1.0,
        }
        stocks[dest_key]["price_modifier"] = 1.0
    return stocks[dest_key]


def generate_default_refined_stock(cargo: dict[str, int]) -> dict[str, Any]:
    """Generate default refined workshop items from delivered raw caravan cargo."""
    unlocked: dict[str, Any] = {}
    for reagent, qty in cargo.items():
        unlocked[f"refined_{reagent}"] = {
            "name": f"Refined {reagent.replace('_', ' ').title()}",
            "price_gold": 25,
            "quantity": qty * 2,
            "rarity": "rare",
        }
    return unlocked


def apply_delivery_success_to_stock(
    stock: dict[str, Any],
    caravan_id: str,
    cargo_delivered: dict[str, int],
    unlocked_stock: dict[str, Any],
) -> None:
    """Record a successful caravan trade delivery into outpost merchant stock."""
    stock["last_delivery"] = caravan_id
    for item, qty in cargo_delivered.items():
        stock["workshop_reagents"][item] = stock["workshop_reagents"].get(item, 0) + qty
    for key, val in unlocked_stock.items():
        stock["inventory"][key] = val

    stats = stock["delivery_stats"]
    stats["total_deliveries"] += 1
    stats["successful_deliveries"] += 1
    stats["success_rate"] = round(stats["successful_deliveries"] / stats["total_deliveries"], 2)
    stock["price_modifier"] = calculate_economic_price_modifier(
        stats["total_deliveries"], stats["successful_deliveries"]
    )


def apply_ambush_stats_to_stock(stock: dict[str, Any], outcome: str) -> None:
    """Update delivery and economic statistics for ambushed trade caravans."""
    stats = stock["delivery_stats"]
    stats["ambushed_deliveries"] += 1
    if outcome == "caravan_destroyed":
        stats["total_deliveries"] += 1
        stats["success_rate"] = round(
            stats["successful_deliveries"] / max(1, stats["total_deliveries"]), 2
        )
        stock["price_modifier"] = calculate_economic_price_modifier(
            stats["total_deliveries"], stats["successful_deliveries"]
        )


def filter_contracts(
    contracts: dict[str, dict[str, Any]],
    risk_level: str | None = None,
    destination: str | None = None,
    status: str | None = None,
    min_reward: int | None = None,
) -> list[dict[str, Any]]:
    """Query available notice board contracts applying optional frontier filters."""
    results: list[dict[str, Any]] = []
    for c in contracts.values():
        if status and c.get("status") != status:
            continue
        if risk_level and c.get("route_risk_level", "").lower() != risk_level.lower():
            continue
        if destination and c.get("destination_outpost", "").lower() != destination.lower():
            continue
        if min_reward is not None and c.get("reward_gold", 0) < min_reward:
            continue
        results.append(c)
    return results


__all__ = [
    "apply_ambush_stats_to_stock",
    "apply_delivery_success_to_stock",
    "calculate_economic_price_modifier",
    "ensure_outpost_stock_entry",
    "filter_contracts",
    "generate_default_refined_stock",
]
