"""Missing player stand-in AI engine with DM penalties and recap generator."""

from typing import Any

from the_watcher.models import StandInAction


class StandInAIEngine:
    """Simulates actions, dialogue, and recaps for absent players."""

    def generate_stand_in_action(
        self,
        character_name: str,
        character_class: str,
        penalties: list[str],
        scene_context: str,
        personality_traits: list[str] | None = None,
    ) -> StandInAction:
        """Simulate an action and dialogue for an absent player's character.

        Applies DM-inflicted penalties ('drunk', 'foolishness', 'cowardice', 'greed')
        and character personality traits ('valiant', 'impulsive', 'scholarly', etc.).
        """
        traits = [t.lower() for t in (personality_traits or [])]
        penalties_lower = [p.lower() for p in penalties]

        if "drunk" in penalties_lower:
            if "scholarly" in traits:
                act = f"{character_name} stumbles forward, slurring arcane citations and swaying on their heels before swinging at a shadow."
                dlg = '"Hic! According to Arcane Volume IV... *burp*... goblins are statistically flammable! The ale only sharpens my blade!"'
            elif "valiant" in traits:
                act = f"{character_name} stands with chest puffed out and eyes crossed, swaying on their heels before swinging valiantly at a shadow."
                dlg = '"Hic! Fear not, companions! Even intoxicated, valor guides my blade! The ale only sharpens my courage!"'
            elif "impulsive" in traits:
                act = f"{character_name} sways wildly on their heels, hiccuping loudly, before recklessly swinging at a shadow."
                dlg = '"Hic! Why formulate a plan? The ale only sharpens my blade! Attack now!"'
            else:
                act = f"{character_name} sways on their heels, hiccuping loudly, before swinging at a shadow."
                dlg = '"Hic! Don\'t you worry, my friends! The ale only sharpens my blade!"'

            return StandInAction(
                character_name=character_name,
                action_type="attack",
                action_description=act,
                dialogue=dlg,
                penalty_influence="Drunk: Disadvantage on finesse, precision, and perception checks (-2 penalty).",
                dice_roll_required="1d20-2",
                penalties_applied=penalties,
                flavor_text=act,
            )

        if "foolishness" in penalties_lower:
            if "scholarly" in traits:
                act = f"{character_name} strides into the open without cover, lecturing the enemy on tactical geometry and creating a massive distraction."
                dlg = '"Danger? Ha! Empirical analysis proves danger is merely theoretical! Follow my glory!"'
            elif "valiant" in traits:
                act = f"{character_name} recklessly charges headfirst towards the most imposing threat in the room, creating an absurd distraction that draws every enemy blade."
                dlg = '"Danger? Ha! I eat danger for breakfast! Follow my glory!"'
            elif "impulsive" in traits:
                act = f"{character_name} dives headfirst into the center of the hostile pack, bellowing a wild battle cry that completely distracts the enemy line."
                dlg = '"Danger? Ha! The more danger, the more fun! Follow my glory!"'
            else:
                act = f"{character_name} recklessly charges headfirst towards the most imposing threat in the room."
                dlg = '"Danger? Ha! I eat danger for breakfast! Follow my glory!"'

            return StandInAction(
                character_name=character_name,
                action_type="attack",
                action_description=act,
                dialogue=dlg,
                penalty_influence="Foolishness: AI ignores tactical cover, creating a brazen distraction that draws enemy threat and imposes disadvantage on enemy attacks against allies.",
                dice_roll_required="1d20",
                penalties_applied=penalties,
                flavor_text=act,
            )

        if "cowardice" in penalties_lower:
            if "scholarly" in traits:
                act = f"{character_name} cites tactical evacuation principles and scurries behind a sturdy stone pillar, entering full defensive posturing."
                dlg = '"Historical treatises state that strategic retreat is the pinnacle of intellectual warfare! I guard our escape vector!"'
            elif "valiant" in traits:
                act = f"{character_name} rapidly retreats behind the largest shield in the room, taking a guarded defensive stance to secure the rear flank."
                dlg = '"A strategic tactical retreat preserves the hero for tomorrow! I shall vigilantly secure the rear!"'
            elif "impulsive" in traits:
                act = f"{character_name} shrieks and bolts behind cover, dropping to a full defensive crouch and scanning for escape routes."
                dlg = '"My gut screams danger, so I am retreating to cover right this second!"'
            else:
                act = f"{character_name} falls back behind cover, taking a guarded defensive posture and scanning frantically for exits."
                dlg = '"Discretion is the better part of valor! I am not fleeing, I am guarding the rear!"'

            return StandInAction(
                character_name=character_name,
                action_type="defend",
                action_description=act,
                dialogue=dlg,
                penalty_influence="Cowardice: Takes full defensive posture / retreat, prioritizing self-preservation and cover.",
                dice_roll_required="1d20+2",
                penalties_applied=penalties,
                flavor_text=act,
            )

        if "greed" in penalties_lower:
            if "scholarly" in traits:
                act = f"{character_name} ignores the combat vanguard to scrutinize an ornate chest, cataloging ancient relics and coins mid-battle."
                dlg = '"Is that authentic First-Age filigree?! Hold the line while I catalogue and secure these priceless antiquities!"'
            elif "valiant" in traits:
                act = f"{character_name} rushes past enemy lines to claim the ornate ceremonial chest, declaring the spoils rightfully belong to the party."
                dlg = '"This treasure must not remain in villainous clutches! I shall secure our rightful spoils!"'
            elif "impulsive" in traits:
                act = f"{character_name} spots a glimmering gemstone on the ground and dives for it immediately, pocketing loot while evading strikes."
                dlg = '"Shiny! Dibs on the gilded chalice before anyone else grabs it!"'
            else:
                act = f"{character_name} disengages from the melee to rummage through a nearby chest and search fallen foes for valuables."
                dlg = '"Look at all that glittering loot! Keep them busy for one moment while I secure our treasure!"'

            return StandInAction(
                character_name=character_name,
                action_type="loot",
                action_description=act,
                dialogue=dlg,
                penalty_influence="Greed: AI prioritizes looting chests, coins, and relics over tactical combat positioning.",
                dice_roll_required="1d20",
                penalties_applied=penalties,
                flavor_text=act,
            )

        # Standard stand-in persona (no penalties applied)
        if "valiant" in traits:
            act = f"{character_name} stands resolute at the vanguard with shield held high, protecting companions and challenging the foe."
            dlg = '"Stand firm, companions! Honor and courage will carry us through!"'
        elif "impulsive" in traits:
            act = f"{character_name} surges forward with sudden momentum, striking the enemy before they can establish formation."
            dlg = '"No more hesitation—strike hard and fast!"'
        elif "scholarly" in traits:
            act = f"{character_name} calculates the enemy's defensive weak points and coordinates a precise tactical strike."
            dlg = '"Their formation has a structural flaw. Focus your strikes on my mark!"'
        else:
            act = f"{character_name} takes a guarded defensive posture, watching the party's flank."
            dlg = '"Hold the line. We press forward together."'

        return StandInAction(
            character_name=character_name,
            action_type="attack",
            action_description=act,
            dialogue=dlg,
            penalty_influence=None,
            dice_roll_required="1d20+2",
            penalties_applied=[],
            flavor_text=act,
        )

    def generate_stand_in_recap(
        self,
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
                desc = (
                    act.get("action_description")
                    or act.get("flavor_text")
                    or act.get("details", "")
                )
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
            f"Welcome back, {character_name}! While you were away, The Watcher piloted your hero through the session."
        ]

        if "drunk" in penalties_list:
            recap_lines.append(
                f"Under the staggering influence of excessive tavern spirits ('drunk'), {character_name} swayed bravely across the battlefield, swinging with -2 disadvantage and slurring battle hymns with absolute conviction."
            )
        if "foolishness" in penalties_list:
            recap_lines.append(
                f"Afflicted with grand 'foolishness', {character_name} treated mortal peril as mere entertainment, taunting colossal foes and single-handedly distracting enemies away from the party."
            )
        if "cowardice" in penalties_list:
            recap_lines.append(
                f"Possessed by a sudden outbreak of 'cowardice', {character_name} redefined the art of tactical retreat, guarding every boulder and doorway with Olympic-level defensive reflexes."
            )
        if "greed" in penalties_list:
            recap_lines.append(
                f"Driven by overwhelming 'greed', {character_name} prioritized securing shiny coins, ornate urns, and forgotten pouches while combat swirled around them."
            )
        if not penalties_list:
            recap_lines.append(
                f"{character_name} acquitted themselves admirably, maintaining defensive cohesion and keeping the party intact."
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
