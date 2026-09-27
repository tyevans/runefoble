"""Absentee chronicle recap generator for missing player AI stand-ins."""

from typing import Any

from the_watcher.models import StandInAction


def generate_absentee_recap(
    character_name: str,
    actions: list[Any],
    penalties: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a humorous absentee session recap for a returning player."""
    penalties_set = {p.lower() for p in (penalties or [])}
    highlights: list[str] = []

    for act in actions:
        if isinstance(act, StandInAction):
            desc = act.action_description
            dlg = act.dialogue
            for p in act.penalties_applied:
                penalties_set.add(p.lower())
            if act.penalty_influence:
                for p in ["drunk", "foolishness", "cowardice", "greed"]:
                    if p in act.penalty_influence.lower():
                        penalties_set.add(p)
        elif isinstance(act, dict):
            desc = act.get("action_description") or act.get("flavor_text") or act.get("details", "")
            dlg = act.get("dialogue", "")
            for p in act.get("penalties_applied", []):
                penalties_set.add(p.lower())
            p_inf = act.get("penalty_influence", "")
            for p in ["drunk", "foolishness", "cowardice", "greed"]:
                if p in p_inf.lower():
                    penalties_set.add(p)
        else:
            desc = str(act)
            dlg = ""

        if desc and len(highlights) < 4:
            item = desc
            if dlg:
                item += f" Shouted: {dlg}"
            highlights.append(item)

    penalties_list = sorted(penalties_set)

    recap_lines = [
        f"Welcome back, {character_name}! While you were away, The Watcher piloted your"
        " hero through the session."
    ]

    if "drunk" in penalties_list:
        recap_lines.append(
            f"Under the staggering influence of excessive tavern spirits ('drunk'),"
            f" {character_name} swayed bravely across the battlefield, swinging with -2"
            " disadvantage and slurring battle hymns with absolute conviction."
        )
    if "foolishness" in penalties_list:
        recap_lines.append(
            f"Afflicted with grand 'foolishness', {character_name} treated mortal peril as"
            " mere entertainment, taunting colossal foes and single-handedly distracting"
            " enemies away from the party."
        )
    if "cowardice" in penalties_list:
        recap_lines.append(
            f"Possessed by a sudden outbreak of 'cowardice', {character_name} redefined the"
            " art of tactical retreat, guarding every boulder and doorway with Olympic-level"
            " defensive reflexes."
        )
    if "greed" in penalties_list:
        recap_lines.append(
            f"Driven by overwhelming 'greed', {character_name} prioritized securing shiny coins,"
            " ornate urns, and forgotten pouches while combat swirled around them."
        )
    if not penalties_list:
        recap_lines.append(
            f"{character_name} acquitted themselves admirably, maintaining defensive"
            " cohesion and keeping the party intact."
        )

    if not highlights:
        highlights = [
            f"{character_name} held the line steadfastly in your absence.",
            "Returned alive with all limbs and inventory accounted for.",
        ]

    full_recap = " ".join(recap_lines)
    return {
        "character_name": character_name,
        "recap": full_recap,
        "highlights": highlights,
        "penalties_active": penalties_list,
    }
