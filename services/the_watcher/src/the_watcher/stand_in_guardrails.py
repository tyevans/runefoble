"""Tactical guardrail policies evaluator for missing player AI stand-ins."""

from typing import Any

from the_watcher.models import StandInAction


def evaluate_tactical_guardrails(
    character_name: str,
    character_class: str,
    penalties: list[str],
    scene_context: str,
    personality_traits: list[str] | None = None,
    guardrails: dict[str, Any] | None = None,
) -> StandInAction | None:
    """Evaluate tactical guardrails: ally protection, spell slot preservation, avoid melee.

    Returns StandInAction if a guardrail policy is triggered, otherwise None.
    """
    if not guardrails:
        return None

    penalties_lower = [p.lower() for p in penalties]
    ctx_lower = scene_context.lower()

    protect_allies = [str(a).strip() for a in guardrails.get("protect_allies", []) if a]
    preserve_slots = guardrails.get("preserve_spell_slots", {})
    avoid_melee = guardrails.get("avoid_melee", False)
    custom_priorities = [str(p).lower() for p in guardrails.get("custom_priorities", [])]

    # 1. Ally Protection Priority
    for ally in protect_allies:
        ally_lower = ally.lower()
        if ally_lower in ctx_lower or ("heal" in ctx_lower and "wounded" in ctx_lower):
            applied = [f"Prioritized protection for {ally}"]
            if "drunk" in penalties_lower:
                dlg = f'"*Hic!* Hold on, {ally}! Even seeing double, my healing light will reach ya! The ale only sharpens my blade!"'
                act = f"{character_name} stumbles over, slurring incantations but faithfully channeling healing magic to protect {ally} as mandated by tactical guardrails."
                pen_inf = "Drunk: Disadvantage on checks (-2 penalty), but tactical guardrail priorities upheld."
                roll = "1d20-2"
            elif "foolishness" in penalties_lower:
                dlg = f'"Fear not, {ally}! I eat danger for breakfast while patching your wounds with glorious radiance!"'
                act = f"{character_name} creates a reckless distraction while casting protective magic on {ally}."
                pen_inf = "Foolishness: AI ignores cover while fulfilling tactical guardrail."
                roll = "1d20"
            else:
                dlg = f'"Hold on, {ally}! Prioritizing your protection with healing light!"'
                act = f"{character_name} casts protective healing on {ally} as prioritized by tactical guardrails."
                pen_inf = None
                roll = "1d20+2"
            return StandInAction(
                character_name=character_name,
                action_type="cast_spell",
                action_description=act,
                dialogue=dlg,
                penalty_influence=pen_inf,
                dice_roll_required=roll,
                penalties_applied=penalties,
                guardrails_applied=applied,
                flavor_text=act,
            )

    # 2. Spell Slot Preservation Limit
    if preserve_slots or any("slot" in p or "revivify" in p for p in custom_priorities):
        res_level = min(int(k) for k in preserve_slots) if preserve_slots else 3
        if "spell" in ctx_lower or "cast" in ctx_lower or "revivify" in ctx_lower:
            applied = [f"Preserved Level {res_level} spell slots"]
            if "drunk" in penalties_lower:
                dlg = f'"*Hic!* Saving Level {res_level} slots for Revivify as ordered! Cantrip it is! The ale only sharpens my blade!"'
                act = f"{character_name} sways on their boots, strictly preserving reserved Level {res_level} spell slots and casting Sacred Flame cantrip instead."
                pen_inf = "Drunk: Disadvantage on checks (-2 penalty), but spell slot reservation guardrails upheld."
                roll = "1d20-2"
            elif "foolishness" in penalties_lower:
                dlg = f'"Observe! I conserve my mighty Level {res_level} slots for true glory while smiting them with basic magic!"'
                act = f"{character_name} grandly announces the preservation of high-level spell slots and casts a cantrip."
                pen_inf = (
                    "Foolishness: Reckless bravado while obeying spell slot preservation guardrail."
                )
                roll = "1d20"
            else:
                dlg = f'"Preserving Level {res_level} spell slots for emergencies; engaging with Sacred Flame cantrip!"'
                act = f"{character_name} conserves high-level spell slots per tactical policy, deploying a cantrip instead."
                pen_inf = None
                roll = "1d20+2"
            return StandInAction(
                character_name=character_name,
                action_type="cast_spell",
                action_description=act,
                dialogue=dlg,
                penalty_influence=pen_inf,
                dice_roll_required=roll,
                penalties_applied=penalties,
                guardrails_applied=applied,
                flavor_text=act,
            )

    # 3. Avoid Frontline Melee
    if avoid_melee or any("avoid" in p and "melee" in p for p in custom_priorities):
        applied = ["Avoided frontline melee"]
        if "drunk" in penalties_lower:
            dlg = '"*Hic!* Frontline is too crowded! Keeping tactical distance! The ale only sharpens my blade!"'
            act = f"{character_name} wobbles backward to avoid frontline melee, engaging from range according to tactical guardrails."
            pen_inf = "Drunk: Disadvantage on checks (-2 penalty), while adhering to avoid-melee guardrail."
            roll = "1d20-2"
        elif "foolishness" in penalties_lower:
            dlg = '"Ha! I don\'t need to touch you fools to defeat you! Behold my tactical ranged superiority!"'
            act = f"{character_name} ostentatiously stays back from melee while taunting foes from distance."
            pen_inf = "Foolishness: Brazen distraction from range."
            roll = "1d20"
        else:
            dlg = '"Maintaining tactical distance from frontline melee. Engaging from range!"'
            act = f"{character_name} maintains distance from frontline melee, deploying ranged options per tactical guardrails."
            pen_inf = None
            roll = "1d20+2"
        return StandInAction(
            character_name=character_name,
            action_type="ranged_attack",
            action_description=act,
            dialogue=dlg,
            penalty_influence=pen_inf,
            dice_roll_required=roll,
            penalties_applied=penalties,
            guardrails_applied=applied,
            flavor_text=act,
        )

    return None
