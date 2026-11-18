"""Mock-mode decision rules for the stand-in graph.

The mock backend makes no model call. These rules apply the typed guardrail policy to the
decision, so mock output shows the same guardrail effects that a model is asked to follow.
A rule reports its GuardrailName only when it changes the decision.
"""

from typing import Any

from runefoble_platform.stand_in_guardrails import GuardrailName, StandInGuardrailPolicy

CASTER_CLASSES = ("cleric", "wizard", "sorcerer", "ranger", "druid")


def mock_stand_in_decision(
    *,
    char_name: str,
    char_class: str,
    penalties: list[str],
    enemies: list[str],
    scene_context: str,
    policy: StandInGuardrailPolicy,
) -> tuple[dict[str, Any], list[GuardrailName]]:
    """Return the mock decision and the guardrail names that changed it."""
    penalty_set = [p.lower().strip() for p in penalties]
    cls = char_class.lower()
    target, priority_hit = _choose_target(enemies, policy.custom_priorities)
    applied: list[GuardrailName] = []

    ally = _ally_to_protect(policy.protect_allies, scene_context)
    if ally is not None:
        decision = _ally_heal_decision(char_name, ally, penalty_set)
        applied.append(GuardrailName.PROTECT_ALLIES)
    elif policy.avoid_melee and cls in CASTER_CLASSES:
        decision = _ranged_decision(char_name, cls, target)
        applied.append(GuardrailName.AVOID_MELEE)
        if priority_hit:
            applied.append(GuardrailName.CUSTOM_PRIORITIES)
    else:
        decision = _penalty_or_default_decision(char_name, char_class, penalty_set, target)
        if priority_hit:
            applied.append(GuardrailName.CUSTOM_PRIORITIES)

    if policy.preserve_spell_slots and decision["action_type"] == "cast_spell":
        # A cantrip spends no slot. The reserved levels stay untouched.
        decision["mechanics"]["spell_level"] = 0
        applied.append(GuardrailName.PRESERVE_SPELL_SLOTS)

    return decision, applied


def _choose_target(enemies: list[str], priorities: list[str]) -> tuple[str, bool]:
    """Return the first enemy named by the priorities, in priority order. Otherwise the first foe."""
    for priority in priorities:
        for enemy in enemies:
            if priority.strip().lower() == enemy.lower():
                return enemy, True
    return (enemies[0] if enemies else "nearest foe"), False


def _ally_to_protect(allies: list[str], scene_context: str) -> str | None:
    """Return the ally to heal when the scene names an ally or mentions healing."""
    if not allies:
        return None
    ctx = scene_context.lower()
    if any(a.lower() in ctx for a in allies) or "heal" in ctx:
        return allies[0]
    return None


def _ally_heal_decision(char_name: str, ally: str, penalty_set: list[str]) -> dict[str, Any]:
    if "drunk" in penalty_set:
        dialogue = f"*Hic* 'Hold on {ally}! Healing light incoming!' *burp*"
        flavor = (
            f"{char_name} sways wildly while channeling healing magic on {ally} per guardrails."
        )
        mechanics = {"action": "heal", "target": ally, "penalty": "drunk"}
    else:
        dialogue = f"'Protecting {ally}! Stand fast!'"
        flavor = f"{char_name} casts protective healing on {ally} obeying tactical guardrails."
        mechanics = {"action": "heal", "target": ally}
    return {
        "action_type": "cast_spell",
        "target": ally,
        "dialogue": dialogue,
        "narrative_flavor": flavor,
        "mechanics": mechanics,
    }


def _ranged_decision(char_name: str, cls: str, target: str) -> dict[str, Any]:
    action_type = "cast_spell" if cls != "ranger" else "ranged_attack"
    return {
        "action_type": action_type,
        "target": target,
        "dialogue": "'Keeping distance from frontline melee as planned!'",
        "narrative_flavor": f"{char_name} maintains safe distance, deploying ranged attacks per tactical guardrails.",
        "mechanics": {"action": action_type, "target": target},
    }


def _penalty_or_default_decision(
    char_name: str, char_class: str, penalty_set: list[str], target: str
) -> dict[str, Any]:
    if "drunk" in penalty_set:
        return {
            "action_type": "attack",
            "target": target,
            "dialogue": "*Hic* 'Stand shtill, ya six-eyed fiend! I got two blades and one of 'em'sh real!'",
            "narrative_flavor": (
                f"{char_name} sways dangerously on one boot, attempting a wide overhand strike at {target} "
                "before stumbling into a nearby barrel."
            ),
            "mechanics": {
                "roll": "1d20-2",
                "condition": "Disadvantage (Intoxicated)",
                "penalty": "drunk",
            },
        }
    if "foolishness" in penalty_set:
        return {
            "action_type": "foolish_act",
            "target": target,
            "dialogue": "'Observe my masterstroke! Never flank when you can charge directly through their spears!'",
            "narrative_flavor": (
                f"{char_name} boldly announces their tactical plan at the top of their lungs, "
                "waving arms wildly to draw all enemy attention."
            ),
            "mechanics": {
                "action": "distraction",
                "penalty": "foolishness",
                "hostile_advantage_granted": True,
            },
        }
    action_type = (
        "attack"
        if char_class.lower() in ["fighter", "barbarian", "rogue", "paladin"]
        else "cast_spell"
    )
    return {
        "action_type": action_type,
        "target": target,
        "dialogue": "'For the realm! Stand firm!'",
        "narrative_flavor": f"{char_name} executes a textbook {char_class} maneuver against {target}.",
        "mechanics": {"action": action_type, "target": target},
    }
