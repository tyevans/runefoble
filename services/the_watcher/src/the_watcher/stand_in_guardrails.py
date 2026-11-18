"""Tactical guardrail evaluator for missing player AI stand-ins (local engine).

Rules run in a fixed order: ally protection, spell slot reserve, custom priority, avoid melee.
The first rule that applies returns the action. Each reported name is a GuardrailName.
"""

from runefoble_platform.stand_in_guardrails import GuardrailName, StandInGuardrailPolicy
from the_watcher.models import StandInAction


def evaluate_tactical_guardrails(
    character_name: str,
    character_class: str,
    penalties: list[str],
    scene_context: str,
    personality_traits: list[str] | None = None,
    guardrails: StandInGuardrailPolicy | None = None,
) -> StandInAction | None:
    """Return the StandInAction of the first guardrail rule that applies, otherwise None."""
    if guardrails is None:
        return None

    penalties_lower = [p.lower() for p in penalties]
    ctx_lower = scene_context.lower()

    for ally in guardrails.protect_allies:
        ally_name = ally.strip()
        if not ally_name:
            continue
        if ally_name.lower() in ctx_lower or ("heal" in ctx_lower and "wounded" in ctx_lower):
            return _ally_action(character_name, ally_name, penalties, penalties_lower)

    if guardrails.preserve_spell_slots and any(
        word in ctx_lower for word in ("spell", "cast", "revivify")
    ):
        res_level = min(guardrails.preserve_spell_slots)
        return _slot_action(character_name, res_level, penalties, penalties_lower)

    for priority in guardrails.custom_priorities:
        if priority.lower() in ctx_lower:
            return _priority_action(character_name, priority, penalties, penalties_lower)

    if guardrails.avoid_melee:
        return _melee_action(character_name, penalties, penalties_lower)

    return None


def _ally_action(
    character_name: str, ally: str, penalties: list[str], penalties_lower: list[str]
) -> StandInAction:
    if "drunk" in penalties_lower:
        dlg = f'"*Hic!* Hold on, {ally}! Even seeing double, my healing light will reach ya! The ale only sharpens my blade!"'
        act = f"{character_name} stumbles over, slurring incantations but faithfully channeling healing magic to protect {ally} as mandated by tactical guardrails."
        pen_inf = (
            "Drunk: Disadvantage on checks (-2 penalty), but tactical guardrail priorities upheld."
        )
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
    return _action(
        character_name,
        "cast_spell",
        act,
        dlg,
        pen_inf,
        roll,
        penalties,
        GuardrailName.PROTECT_ALLIES,
    )


def _slot_action(
    character_name: str, res_level: int, penalties: list[str], penalties_lower: list[str]
) -> StandInAction:
    if "drunk" in penalties_lower:
        dlg = f'"*Hic!* Saving Level {res_level} slots for Revivify as ordered! Cantrip it is! The ale only sharpens my blade!"'
        act = f"{character_name} sways on their boots, strictly preserving reserved Level {res_level} spell slots and casting Sacred Flame cantrip instead."
        pen_inf = "Drunk: Disadvantage on checks (-2 penalty), but spell slot reservation guardrails upheld."
        roll = "1d20-2"
    elif "foolishness" in penalties_lower:
        dlg = f'"Observe! I conserve my mighty Level {res_level} slots for true glory while smiting them with basic magic!"'
        act = f"{character_name} grandly announces the preservation of high-level spell slots and casts a cantrip."
        pen_inf = "Foolishness: Reckless bravado while obeying spell slot preservation guardrail."
        roll = "1d20"
    else:
        dlg = f'"Preserving Level {res_level} spell slots for emergencies; engaging with Sacred Flame cantrip!"'
        act = f"{character_name} conserves high-level spell slots per tactical policy, deploying a cantrip instead."
        pen_inf = None
        roll = "1d20+2"
    return _action(
        character_name,
        "cast_spell",
        act,
        dlg,
        pen_inf,
        roll,
        penalties,
        GuardrailName.PRESERVE_SPELL_SLOTS,
    )


def _priority_action(
    character_name: str, priority: str, penalties: list[str], penalties_lower: list[str]
) -> StandInAction:
    if "drunk" in penalties_lower:
        dlg = f'"*Hic!* {priority} first! Swinging at them! The ale only sharpens my blade!"'
        pen_inf = "Drunk: Disadvantage on checks (-2 penalty), but the priority order is upheld."
        roll = "1d20-2"
    elif "foolishness" in penalties_lower:
        dlg = f'"{priority}? Easy! I will charge them all at once!"'
        pen_inf = "Foolishness: Reckless charge at the prioritized target."
        roll = "1d20"
    else:
        dlg = f'"{priority} first. Engaging now!"'
        pen_inf = None
        roll = "1d20+2"
    act = f"{character_name} focuses on {priority} as ordered by tactical priorities."
    return _action(
        character_name,
        "attack",
        act,
        dlg,
        pen_inf,
        roll,
        penalties,
        GuardrailName.CUSTOM_PRIORITIES,
    )


def _melee_action(
    character_name: str, penalties: list[str], penalties_lower: list[str]
) -> StandInAction:
    if "drunk" in penalties_lower:
        dlg = '"*Hic!* Frontline is too crowded! Keeping tactical distance! The ale only sharpens my blade!"'
        act = f"{character_name} wobbles backward to avoid frontline melee, engaging from range according to tactical guardrails."
        pen_inf = (
            "Drunk: Disadvantage on checks (-2 penalty), while adhering to avoid-melee guardrail."
        )
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
    return _action(
        character_name,
        "ranged_attack",
        act,
        dlg,
        pen_inf,
        roll,
        penalties,
        GuardrailName.AVOID_MELEE,
    )


def _action(
    character_name: str,
    action_type: str,
    act: str,
    dlg: str,
    pen_inf: str | None,
    roll: str,
    penalties: list[str],
    guardrail: GuardrailName,
) -> StandInAction:
    return StandInAction(
        character_name=character_name,
        action_type=action_type,
        action_description=act,
        dialogue=dlg,
        penalty_influence=pen_inf,
        dice_roll_required=roll,
        penalties_applied=penalties,
        guardrails_applied=[guardrail],
        flavor_text=act,
    )
