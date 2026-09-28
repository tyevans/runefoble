"""Rules engine for mobile tavern and casino minigames suite.

Governed by ADR-0004, ADR-0006, ADR-0012, PRD-0024, and US-0074.
Provides mathematical evaluation, collision/trajectory projection, and payout calculations.
"""

from __future__ import annotations

import math
from typing import Any

# Standard 20-sector dartboard sequence clockwise starting from top
DARTBOARD_SECTORS: list[int] = [
    20,
    1,
    18,
    4,
    13,
    6,
    10,
    15,
    2,
    17,
    3,
    19,
    7,
    16,
    8,
    11,
    14,
    9,
    12,
    5,
]

ROULETTE_RED_NUMBERS: set[int] = {
    1,
    3,
    5,
    7,
    9,
    12,
    14,
    16,
    18,
    19,
    21,
    23,
    25,
    27,
    30,
    32,
    34,
    36,
}


def calculate_dart_trajectory(
    vx: float,
    vy: float,
    wind_x: float = 0.0,
    wind_y: float = 0.0,
    drag: float = 0.95,
) -> tuple[float, float]:
    """Project dart flick velocity onto the board plane with aerodynamic drag and wind."""
    # Terminal coordinates relative to bullseye center (0, 0)
    tx = (vx * 15.0 * drag) + (wind_x * 8.0)
    ty = (vy * 15.0 * drag) + (wind_y * 8.0)
    return tx, ty


def score_dart_hit(x: float, y: float) -> dict[str, Any]:
    """Score a dart hit based on radius (mm) and angle from board center."""
    radius = math.hypot(x, y)
    angle_deg = (math.degrees(math.atan2(y, x)) + 90) % 360  # 0 deg = top (20)

    # Bullseye check
    if radius <= 6.35:
        return {"sector": 50, "ring": "inner_bull", "points": 50, "name": "Double Bullseye"}
    if radius <= 15.9:
        return {"sector": 25, "ring": "outer_bull", "points": 25, "name": "Bullseye"}
    if radius > 170.0:
        return {"sector": 0, "ring": "miss", "points": 0, "name": "Miss"}

    # Sector calculation: 20 sectors, each 18 degrees wide, centered on sector
    sector_idx = int(((angle_deg + 9) % 360) // 18)
    sector_val = DARTBOARD_SECTORS[sector_idx]

    if 97.0 <= radius <= 107.0:
        return {
            "sector": sector_val,
            "ring": "triple",
            "points": sector_val * 3,
            "name": f"Triple {sector_val}",
        }
    if 162.0 <= radius <= 170.0:
        return {
            "sector": sector_val,
            "ring": "double",
            "points": sector_val * 2,
            "name": f"Double {sector_val}",
        }

    return {
        "sector": sector_val,
        "ring": "single",
        "points": sector_val,
        "name": f"Single {sector_val}",
    }


def evaluate_darts_501_throw(
    current_score: int,
    hit_points: int,
    double_out: bool = False,
    is_double: bool = False,
) -> tuple[int, bool, bool]:
    """Calculate remaining 501 score, bust status, and victory status."""
    new_score = current_score - hit_points
    if new_score == 0:
        if double_out and not is_double:
            return current_score, True, False  # Bust: must finish on a double
        return 0, False, True  # Won!
    if new_score < 0 or (double_out and new_score == 1):
        return current_score, True, False  # Bust
    return new_score, False, False


def get_roulette_color(number: int) -> str:
    """Return red, black, or green for a roulette number (0-36)."""
    if number == 0:
        return "green"
    return "red" if number in ROULETTE_RED_NUMBERS else "black"


def evaluate_roulette_bets(winning_number: int, bets: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate payouts for standard European roulette bets."""
    color = get_roulette_color(winning_number)
    is_even = (winning_number % 2 == 0) and (winning_number != 0)
    is_low = 1 <= winning_number <= 18
    is_high = 19 <= winning_number <= 36

    payouts: dict[str, int] = {}
    winning_bets: list[dict[str, Any]] = []

    for bet in bets:
        player_id = bet["player_id"]
        bet_type = bet.get("bet_type", "straight")
        amount = int(bet.get("amount", 0))
        target = bet.get("target")

        win_multiplier = 0
        if bet_type == "straight" and target == winning_number:
            win_multiplier = 36  # 35:1 payout + original stake
        elif bet_type == "color" and target == color:
            win_multiplier = 2  # 1:1 payout + original stake
        elif bet_type == "even_odd":
            if (target == "even" and is_even) or (
                target == "odd" and not is_even and winning_number != 0
            ):
                win_multiplier = 2
        elif bet_type == "high_low":
            if (target == "low" and is_low) or (target == "high" and is_high):
                win_multiplier = 2
        elif bet_type == "dozen":
            target_int = int(target or 1)
            if (
                (target_int == 1 and 1 <= winning_number <= 12)
                or (target_int == 2 and 13 <= winning_number <= 24)
                or (target_int == 3 and 25 <= winning_number <= 36)
            ):
                win_multiplier = 3

        if win_multiplier > 0:
            won_payout = amount * win_multiplier
            payouts[player_id] = payouts.get(player_id, 0) + won_payout
            winning_bets.append({**bet, "payout": won_payout})

    return {
        "winning_number": winning_number,
        "color": color,
        "payouts": payouts,
        "winning_bets": winning_bets,
    }


def evaluate_craps_roll(
    dice: list[int],
    point: int | None,
    bets: list[dict[str, Any]],
) -> tuple[int | None, dict[str, int], list[dict[str, Any]], str]:
    """Evaluate come-out and point-phase rolls in Dragon Craps."""
    total = sum(dice)
    new_point = point
    payouts: dict[str, int] = {}
    winning_bets: list[dict[str, Any]] = []
    narrative: str

    if point is None:
        # Come-out roll
        if total in (7, 11):
            narrative = f"Natural {total}! Pass line wins!"
            for bet in bets:
                if bet.get("bet_type") == "pass_line":
                    p = bet["amount"] * 2
                    payouts[bet["player_id"]] = payouts.get(bet["player_id"], 0) + p
                    winning_bets.append({**bet, "payout": p})
        elif total in (2, 3, 12):
            narrative = f"Craps ({total})! Pass line loses!"
            for bet in bets:
                if bet.get("bet_type") == "dont_pass":
                    p = bet["amount"] * 2
                    payouts[bet["player_id"]] = payouts.get(bet["player_id"], 0) + p
                    winning_bets.append({**bet, "payout": p})
        else:
            new_point = total
            narrative = f"The point is established at {total}!"
    else:
        # Point phase
        if total == point:
            narrative = f"Hit the point {point}! Pass line wins!"
            new_point = None
            for bet in bets:
                if bet.get("bet_type") == "pass_line":
                    p = bet["amount"] * 2
                    payouts[bet["player_id"]] = payouts.get(bet["player_id"], 0) + p
                    winning_bets.append({**bet, "payout": p})
        elif total == 7:
            narrative = "Seven out! Line away!"
            new_point = None
            for bet in bets:
                if bet.get("bet_type") == "dont_pass":
                    p = bet["amount"] * 2
                    payouts[bet["player_id"]] = payouts.get(bet["player_id"], 0) + p
                    winning_bets.append({**bet, "payout": p})
        else:
            narrative = f"Rolled {total}. Point is still {point}."

    # Field bet evaluations (single roll)
    for bet in bets:
        if bet.get("bet_type") == "field":
            if total in (3, 4, 9, 10, 11):
                p = bet["amount"] * 2
                payouts[bet["player_id"]] = payouts.get(bet["player_id"], 0) + p
                winning_bets.append({**bet, "payout": p})
            elif total == 2:
                p = bet["amount"] * 3  # double on 2
                payouts[bet["player_id"]] = payouts.get(bet["player_id"], 0) + p
                winning_bets.append({**bet, "payout": p})
            elif total == 12:
                p = bet["amount"] * 4  # triple on 12
                payouts[bet["player_id"]] = payouts.get(bet["player_id"], 0) + p
                winning_bets.append({**bet, "payout": p})

    return new_point, payouts, winning_bets, narrative
