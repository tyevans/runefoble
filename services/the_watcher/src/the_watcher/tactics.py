"""Autonomous DM NPC and Monster Combat Tactics.

Adjudicates tactical combat decision trees, spellcaster prioritization,
wounded target finishing heuristics, and combat action resolution.
"""

from __future__ import annotations

from typing import Any

from runefoble_events.events import AutonomousActionResolved

CASTER_KEYWORDS: tuple[str, ...] = (
    "shaman",
    "mage",
    "caster",
    "wraith",
    "cultist",
    "priest",
    "lich",
    "witch",
    "wizard",
)

SPELL_NAMES: tuple[str, ...] = (
    "Ray of Enfeeblement",
    "Shadow Bolt",
    "Misty Step & Fire Bolt",
    "Chaos Spark",
)


def adjudicate_npc_turn(
    session_id: str,
    encounter_id: str,
    actor_name: str,
    targets: list[dict[str, Any]],
    round_number: int = 1,
) -> AutonomousActionResolved:
    """Adjudicate tactical combat decision tree for an NPC or monster."""
    if not targets:
        return AutonomousActionResolved(
            session_id=session_id,
            actor_name=actor_name,
            action_type="search",
            target_name="None",
            narrative=(
                f"{actor_name} scans the shadows in round {round_number}, seeking active threats."
            ),
            hp_impact=0,
        )

    valid_targets = [t for t in targets if t.get("current_hp", t.get("hp", 1)) > 0] or targets
    sorted_targets = sorted(valid_targets, key=lambda t: t.get("current_hp", t.get("hp", 100)))
    chosen_target = sorted_targets[0]
    target_name = chosen_target.get("name", "the party hero")
    target_hp = chosen_target.get("current_hp", chosen_target.get("hp", 20))

    actor_lower = actor_name.lower()
    is_caster = any(kw in actor_lower for kw in CASTER_KEYWORDS)

    if is_caster:
        action_type = "cast_spell"
        chosen_spell = SPELL_NAMES[(round_number - 1) % len(SPELL_NAMES)]
        hp_impact = -8
        narrative = (
            f"{actor_name} channels forbidden incantations in round {round_number},"
            f" unleashing {chosen_spell} directly into {target_name} for"
            f" {abs(hp_impact)} necrotic damage!"
        )
    elif target_hp <= 10:
        action_type = "execute_strike"
        hp_impact = -10
        narrative = (
            f"Sensing vulnerability, {actor_name} lunges at the heavily wounded {target_name} with"
            f" ruthless precision, delivering a finishing blow for {abs(hp_impact)} damage!"
        )
    elif round_number == 1:
        action_type = "charge_attack"
        hp_impact = -6
        narrative = (
            f"{actor_name} breaks from cover in an aggressive charge, slamming their weapon toward"
            f" {target_name}'s exposed flank for {abs(hp_impact)} damage!"
        )
    else:
        action_type = "melee_strike"
        hp_impact = -7
        narrative = (
            f"{actor_name} strikes forcefully against {target_name} in round {round_number},"
            f" inflicting {abs(hp_impact)} slashing damage!"
        )

    return AutonomousActionResolved(
        session_id=session_id,
        actor_name=actor_name,
        action_type=action_type,
        target_name=target_name,
        narrative=narrative,
        hp_impact=hp_impact,
    )
