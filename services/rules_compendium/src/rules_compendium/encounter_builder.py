"""Challenge Rating (CR) encounter balancing engine for 5e rules."""

from typing import Any

from rules_compendium.models import (
    MonsterGroupRecommendation,
)
from rules_compendium.srd_data import CANONICAL_MONSTERS

# Standard 5e XP Thresholds by character level
XP_THRESHOLDS: dict[int, dict[str, int]] = {
    1: {"easy": 25, "medium": 50, "hard": 75, "deadly": 100},
    2: {"easy": 50, "medium": 100, "hard": 150, "deadly": 200},
    3: {"easy": 75, "medium": 150, "hard": 225, "deadly": 400},
    4: {"easy": 125, "medium": 250, "hard": 375, "deadly": 500},
    5: {"easy": 250, "medium": 500, "hard": 750, "deadly": 1100},
    6: {"easy": 300, "medium": 600, "hard": 900, "deadly": 1400},
    7: {"easy": 350, "medium": 750, "hard": 1100, "deadly": 1700},
    8: {"easy": 450, "medium": 900, "hard": 1400, "deadly": 2100},
    9: {"easy": 550, "medium": 1100, "hard": 1600, "deadly": 2400},
    10: {"easy": 600, "medium": 1200, "hard": 1900, "deadly": 2800},
    11: {"easy": 800, "medium": 1600, "hard": 2400, "deadly": 3600},
    12: {"easy": 1000, "medium": 2000, "hard": 3000, "deadly": 4500},
    13: {"easy": 1100, "medium": 2200, "hard": 3400, "deadly": 5100},
    14: {"easy": 1250, "medium": 2500, "hard": 3800, "deadly": 5700},
    15: {"easy": 1400, "medium": 2800, "hard": 4300, "deadly": 6400},
    16: {"easy": 1600, "medium": 3200, "hard": 4800, "deadly": 7200},
    17: {"easy": 2000, "medium": 3900, "hard": 5900, "deadly": 8800},
    18: {"easy": 2100, "medium": 4200, "hard": 6300, "deadly": 9500},
    19: {"easy": 2400, "medium": 4900, "hard": 7300, "deadly": 10900},
    20: {"easy": 2800, "medium": 5700, "hard": 8500, "deadly": 12700},
}


def calculate_party_thresholds(party_levels: list[int]) -> dict[str, int]:
    """Calculate aggregate XP thresholds (easy, medium, hard, deadly) for a party roster."""
    totals = {"easy": 0, "medium": 0, "hard": 0, "deadly": 0}
    for level in party_levels:
        clamped_level = max(1, min(20, level))
        lvl_thresholds = XP_THRESHOLDS[clamped_level]
        for tier in totals:
            totals[tier] += lvl_thresholds[tier]
    return totals


def get_encounter_multiplier(monster_count: int, party_size: int) -> float:
    """Compute action economy encounter multiplier based on monster count and party size."""
    if monster_count <= 0:
        return 1.0

    # Base multiplier tier indexing
    if monster_count == 1:
        tier_index = 1  # 1.0
    elif monster_count == 2:
        tier_index = 2  # 1.5
    elif 3 <= monster_count <= 6:
        tier_index = 3  # 2.0
    elif 7 <= monster_count <= 10:
        tier_index = 4  # 2.5
    elif 11 <= monster_count <= 14:
        tier_index = 5  # 3.0
    else:
        tier_index = 6  # 4.0

    # Party size shift: < 3 members shifts multiplier up; >= 6 members shifts down
    if party_size < 3:
        tier_index = min(7, tier_index + 1)
    elif party_size >= 6:
        tier_index = max(0, tier_index - 1)

    multipliers = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
    return multipliers[tier_index]


def evaluate_encounter_difficulty(adjusted_xp: int, thresholds: dict[str, int]) -> str:
    """Evaluate encounter difficulty tier given adjusted XP and party thresholds."""
    if adjusted_xp < thresholds["easy"]:
        return "Trivial"
    if adjusted_xp < thresholds["medium"]:
        return "Easy"
    if adjusted_xp < thresholds["hard"]:
        return "Medium"
    if adjusted_xp < thresholds["deadly"]:
        return "Hard"
    return "Deadly"


def build_balanced_encounter(
    party_levels: list[int],
    target_difficulty: str = "Medium",
    desired_roles: list[str] | None = None,
    available_monsters: list[dict[str, Any]] | None = None,
) -> tuple[list[MonsterGroupRecommendation], int, float, int, str]:
    """Generate a synergistic monster group matching target difficulty and role synergy.

    Returns:
        (recommended_monsters, total_raw_xp, multiplier, adjusted_xp, calculated_tier)
    """
    thresholds = calculate_party_thresholds(party_levels)
    target_key = target_difficulty.lower()
    if target_key not in thresholds:
        target_key = "medium"

    target_xp = thresholds[target_key]
    party_size = max(1, len(party_levels))
    monsters_pool = available_monsters if available_monsters is not None else CANONICAL_MONSTERS

    # Group available monsters by role
    brutes = [m for m in monsters_pool if m.get("role") == "brute"]
    artillery = [m for m in monsters_pool if m.get("role") in ("artillery", "skirmisher")]
    controllers = [m for m in monsters_pool if m.get("role") in ("controller", "leader")]
    all_sorted = sorted(monsters_pool, key=lambda m: m["xp"])

    best_group: list[dict[str, Any]] = []
    best_diff = float("inf")
    best_raw_xp = 0
    best_adj_xp = 0
    best_mult = 1.0

    # Desired role templates:
    # 1. Standard mixed squad: 1 brute + 2 artillery/skirmishers + 1 controller
    # 2. Heavy brute squad: 2-3 brutes + 1 artillery
    # 3. Swarm skirmish: 4-6 skirmishers/artillery
    # 4. Boss solo/duo: 1 large creature + minion
    candidate_templates = [
        # (brute_count, artillery_count, controller_count)
        (1, 2, 1),
        (2, 2, 0),
        (1, 1, 1),
        (2, 1, 1),
        (1, 3, 0),
        (0, 4, 1),
        (1, 0, 0),
        (2, 0, 0),
    ]

    for b_cnt, a_cnt, c_cnt in candidate_templates:
        total_count = b_cnt + a_cnt + c_cnt
        if total_count == 0:
            continue
        mult = get_encounter_multiplier(total_count, party_size)
        raw_budget = target_xp / mult

        # Pick appropriate monsters for each role
        chosen: list[dict[str, Any]] = []

        if b_cnt > 0 and brutes:
            # find brute whose xp * b_cnt fits roughly 40-60% of budget
            b_target = (raw_budget * 0.5) / b_cnt
            b_choice = min(brutes, key=lambda m: abs(m["xp"] - b_target))
            chosen.append({"monster": b_choice, "count": b_cnt})

        if a_cnt > 0 and artillery:
            a_target = (raw_budget * 0.3) / a_cnt
            a_choice = min(artillery, key=lambda m: abs(m["xp"] - a_target))
            chosen.append({"monster": a_choice, "count": a_cnt})

        if c_cnt > 0 and controllers:
            c_target = (raw_budget * 0.2) / c_cnt
            c_choice = min(controllers, key=lambda m: abs(m["xp"] - c_target))
            chosen.append({"monster": c_choice, "count": c_cnt})

        if not chosen:
            continue

        raw_xp = sum(item["monster"]["xp"] * item["count"] for item in chosen)
        adj_xp = int(raw_xp * mult)
        diff = abs(adj_xp - target_xp)

        if diff < best_diff:
            best_diff = diff
            best_group = chosen
            best_raw_xp = raw_xp
            best_adj_xp = adj_xp
            best_mult = mult

    # Fallback if no template worked
    if not best_group:
        closest = min(all_sorted, key=lambda m: abs(m["xp"] - target_xp))
        best_group = [{"monster": closest, "count": 1}]
        best_raw_xp = closest["xp"]
        best_mult = get_encounter_multiplier(1, party_size)
        best_adj_xp = int(best_raw_xp * best_mult)

    recommendations: list[MonsterGroupRecommendation] = []
    for item in best_group:
        m = item["monster"]
        count = item["count"]
        recommendations.append(
            MonsterGroupRecommendation(
                name=m["name"],
                cr=float(m["challenge_rating"]),
                xp=int(m["xp"]),
                count=count,
                role=m.get("role", "brute"),
                subtotal_xp=int(m["xp"] * count),
            )
        )

    calculated_tier = evaluate_encounter_difficulty(best_adj_xp, thresholds)
    return recommendations, best_raw_xp, best_mult, best_adj_xp, calculated_tier
