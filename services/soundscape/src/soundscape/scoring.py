"""Encounter tension scoring engine (TASK-0050, PRD-0010, US-0039).

Calculates a real-time encounter tension index (0-100) dynamically derived from:
1. Combat round progression (escalating stakes over time)
2. Active enemy Challenge Rating (CR) balance
3. Lowest party member health ratios (near-death spikes)
"""

from __future__ import annotations


def calculate_encounter_tension(
    combat_active: bool,
    combat_round: int = 1,
    enemy_cr_balance: float = 1.0,
    lowest_party_health_ratio: float = 1.0,
) -> int:
    """Compute real-time tension metric (0-100) for a game session.

    Args:
        combat_active: True if initiative combat encounter is currently active.
        combat_round: Number of combat rounds elapsed.
        enemy_cr_balance: Relative ratio or total threat of active enemy CR.
        lowest_party_health_ratio: Lowest current HP / max HP across all player characters (0.0 to 1.0).

    Returns:
        Integer score in the range [0, 100].
    """
    if not combat_active:
        # Ambient exploration phase
        ambient_factor = min(15, max(0, int(enemy_cr_balance * 3)))
        return min(25, max(0, 10 + ambient_factor))

    # Base combat floor
    base_combat = 40

    # 1. Combat round progression (up to +20 points)
    round_progression = min(20, max(0, combat_round * 5))

    # 2. Enemy Challenge Rating threat balance (up to +20 points)
    cr_threat = min(20, max(0, int(enemy_cr_balance * 5)))

    # 3. Lowest party health ratio (near-death peril, up to +40 points)
    clamped_hp_ratio = max(0.0, min(1.0, lowest_party_health_ratio))
    hp_deficit = 1.0 - clamped_hp_ratio
    health_penalty = int(hp_deficit * 25)

    # Mortal danger bonus when any player falls below 25% HP
    critical_spike = 15 if clamped_hp_ratio < 0.25 else 0

    total_score = base_combat + round_progression + cr_threat + health_penalty + critical_spike
    return min(100, max(0, total_score))


def derive_stem_profile(tension_score: int) -> str:
    """Map a tension score (0-100) to an adaptive audio stem profile.

    Profiles:
    - 0-29: exploration (gentle atmosphere, dungeon dripping, wind)
    - 30-59: tension (ominous cello, rising suspense, ticking clock)
    - 60-84: combat (driving battle percussion, brass, high energy)
    - 85-100: boss (epic choir, heavy drums, climax stakes)
    """
    if tension_score < 30:
        return "exploration"
    elif tension_score < 60:
        return "tension"
    elif tension_score < 85:
        return "combat"
    else:
        return "boss"
