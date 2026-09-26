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
        guardrails: dict[str, Any] | None = None,
    ) -> StandInAction:
        """Simulate an action and dialogue for an absent player's character.

        Applies tactical guardrail policies, DM-inflicted penalties
        ('drunk', 'foolishness', 'cowardice', 'greed'), and character personality traits.
        """
        traits = [t.lower() for t in (personality_traits or [])]
        penalties_lower = [p.lower() for p in penalties]
        ctx_lower = scene_context.lower()

        # -------------------------------------------------------------------
        # Tactical Policy Guardrails Evaluation (US-0025)
        # -------------------------------------------------------------------
        if guardrails:
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
                        pen_inf = (
                            "Foolishness: AI ignores cover while fulfilling tactical guardrail."
                        )
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
                res_level = min(preserve_slots.keys()) if preserve_slots else 3
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
                        pen_inf = "Foolishness: Reckless bravado while obeying spell slot preservation guardrail."
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
                    dlg = (
                        '"Maintaining tactical distance from frontline melee. Engaging from range!"'
                    )
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
