"""Persona and penalty simulator for missing player AI stand-ins."""

from the_watcher.models import StandInAction

_INFLUENCE = {
    "drunk": "Drunk: Disadvantage on finesse, precision, and perception checks (-2 penalty).",
    "foolishness": (
        "Foolishness: AI ignores tactical cover, creating a brazen distraction that draws"
        " enemy threat and imposes disadvantage on enemy attacks against allies."
    ),
    "cowardice": (
        "Cowardice: Takes full defensive posture / retreat, prioritizing self-preservation and"
        " cover."
    ),
    "greed": "Greed: AI prioritizes looting chests, coins, and relics over tactical combat positioning.",
}
_DICE = {"drunk": "1d20-2", "cowardice": "1d20+2", "standard": "1d20+2"}
_STANDARD_PRIORITY = ("valiant", "impulsive", "scholarly")
_DEFAULT_PRIORITY = ("scholarly", "valiant", "impulsive")

_TEMPLATES: dict[tuple[str, str], tuple[str, str]] = {
    ("drunk", "scholarly"): (
        "{n} stumbles forward, slurring arcane citations and swaying on their heels before swinging at a shadow.",
        '"Hic! According to Arcane Volume IV... *burp*... goblins are statistically flammable! The ale only sharpens my blade!"',
    ),
    ("drunk", "valiant"): (
        "{n} stands with chest puffed out and eyes crossed, swaying on their heels before swinging valiantly at a shadow.",
        '"Hic! Fear not, companions! Even intoxicated, valor guides my blade! The ale only sharpens my courage!"',
    ),
    ("drunk", "impulsive"): (
        "{n} sways wildly on their heels, hiccuping loudly, before recklessly swinging at a shadow.",
        '"Hic! Why formulate a plan? The ale only sharpens my blade! Attack now!"',
    ),
    ("drunk", "default"): (
        "{n} sways on their heels, hiccuping loudly, before swinging at a shadow.",
        '"Hic! Don\'t you worry, my friends! The ale only sharpens my blade!"',
    ),
    ("foolishness", "scholarly"): (
        "{n} strides into the open without cover, lecturing the enemy on tactical geometry and creating a massive distraction.",
        '"Danger? Ha! Empirical analysis proves danger is merely theoretical! Follow my glory!"',
    ),
    ("foolishness", "valiant"): (
        "{n} recklessly charges headfirst towards the most imposing threat in the room, creating an absurd distraction that draws every enemy blade.",
        '"Danger? Ha! I eat danger for breakfast! Follow my glory!"',
    ),
    ("foolishness", "impulsive"): (
        "{n} dives headfirst into the center of the hostile pack, bellowing a wild battle cry that completely distracts the enemy line.",
        '"Danger? Ha! The more danger, the more fun! Follow my glory!"',
    ),
    ("foolishness", "default"): (
        "{n} recklessly charges headfirst towards the most imposing threat in the room.",
        '"Danger? Ha! I eat danger for breakfast! Follow my glory!"',
    ),
    ("cowardice", "scholarly"): (
        "{n} cites tactical evacuation principles and scurries behind a sturdy stone pillar, entering full defensive posturing.",
        '"Historical treatises state that strategic retreat is the pinnacle of intellectual warfare! I guard our escape vector!"',
    ),
    ("cowardice", "valiant"): (
        "{n} rapidly retreats behind the largest shield in the room, taking a guarded defensive stance to secure the rear flank.",
        '"A strategic tactical retreat preserves the hero for tomorrow! I shall vigilantly secure the rear!"',
    ),
    ("cowardice", "impulsive"): (
        "{n} shrieks and bolts behind cover, dropping to a full defensive crouch and scanning for escape routes.",
        '"My gut screams danger, so I am retreating to cover right this second!"',
    ),
    ("cowardice", "default"): (
        "{n} falls back behind cover, taking a guarded defensive posture and scanning frantically for exits.",
        '"Discretion is the better part of valor! I am not fleeing, I am guarding the rear!"',
    ),
    ("greed", "scholarly"): (
        "{n} ignores the combat vanguard to scrutinize an ornate chest, cataloging ancient relics and coins mid-battle.",
        '"Is that authentic First-Age filigree?! Hold the line while I catalogue and secure these priceless antiquities!"',
    ),
    ("greed", "valiant"): (
        "{n} rushes past enemy lines to claim the ornate ceremonial chest, declaring the spoils rightfully belong to the party.",
        '"This treasure must not remain in villainous clutches! I shall secure our rightful spoils!"',
    ),
    ("greed", "impulsive"): (
        "{n} spots a glimmering gemstone on the ground and dives for it immediately, pocketing loot while evading strikes.",
        '"Shiny! Dibs on the gilded chalice before anyone else grabs it!"',
    ),
    ("greed", "default"): (
        "{n} disengages from the melee to rummage through a nearby chest and search fallen foes for valuables.",
        '"Look at all that glittering loot! Keep them busy for one moment while I secure our treasure!"',
    ),
    ("standard", "valiant"): (
        "{n} stands resolute at the vanguard with shield held high, protecting companions and challenging the foe.",
        '"Stand firm, companions! Honor and courage will carry us through!"',
    ),
    ("standard", "impulsive"): (
        "{n} surges forward with sudden momentum, striking the enemy before they can establish formation.",
        '"No more hesitation—strike hard and fast!"',
    ),
    ("standard", "scholarly"): (
        "{n} calculates the enemy's defensive weak points and coordinates a precise tactical strike.",
        '"Their formation has a structural flaw. Focus your strikes on my mark!"',
    ),
    ("standard", "default"): (
        "{n} takes a guarded defensive posture, watching the party's flank.",
        '"Hold the line. We press forward together."',
    ),
}


def apply_penalty_modifiers(
    character_name: str,
    character_class: str,
    penalties: list[str],
    scene_context: str,
    personality_traits: list[str] | None = None,
) -> StandInAction:
    """Inject humorous DM-inflicted penalties and character personality traits into actions."""
    traits = {t.lower() for t in (personality_traits or [])}
    penalties_lower = [p.lower() for p in penalties]

    penalty = next(
        (p for p in ("drunk", "foolishness", "cowardice", "greed") if p in penalties_lower),
        "standard",
    )
    action_type = (
        "defend" if penalty == "cowardice" else ("loot" if penalty == "greed" else "attack")
    )
    priority = _STANDARD_PRIORITY if penalty == "standard" else _DEFAULT_PRIORITY

    matched_trait = next((t for t in priority if t in traits), "default")
    act_tpl, dlg = _TEMPLATES[(penalty, matched_trait)]
    act = act_tpl.format(n=character_name)

    return StandInAction(
        character_name=character_name,
        action_type=action_type,
        action_description=act,
        dialogue=dlg,
        penalty_influence=_INFLUENCE.get(penalty),
        dice_roll_required=_DICE.get(penalty, "1d20"),
        penalties_applied=penalties if penalty != "standard" else [],
        flavor_text=act,
    )
