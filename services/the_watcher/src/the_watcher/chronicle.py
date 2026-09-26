"""Absentee session chronicle and recap engine for returning players."""

from typing import Any
from uuid import UUID, uuid4

from runefoble_events.events import AbsenteeRecapGenerated


def _to_uuid(val: Any) -> UUID:
    """Coerce string or UUID to UUID."""
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except (ValueError, AttributeError):
        return uuid4()


class ChronicleRecapEngine:
    """Composes humorous, persona-driven session chronicles for absent players."""

    def generate_recap(
        self,
        session_id: str,
        character_id: str,
        character_name: str,
        stand_in_persona: str,
        penalties: list[str],
        actions: list[dict[str, Any]] | None = None,
        hp_delta: int = 0,
        items_acquired: list[str] | None = None,
        audio_url: str | None = None,
    ) -> AbsenteeRecapGenerated:
        """Generate a humorous absentee chronicle and dispatch-ready domain event."""
        actions_list = actions or []
        items_list = list(items_acquired or [])
        penalties_norm = [p.lower().strip() for p in penalties]
        persona_norm = stand_in_persona.lower().strip()

        # Build narrative chronicle segments
        narrative_parts: list[str] = [
            f"Welcome back, {character_name}! While you were away from the realm, The Watcher assumed control "
            f"under the guise of the '{stand_in_persona}' persona."
        ]

        # Humorous penalty narratives
        if "drunk" in penalties_norm:
            narrative_parts.append(
                f"Severely impaired by an overabundance of tavern spirits ('drunk'), {character_name} swayed violently "
                f"across the stone floor, belting out slurred battlecries between thunderous hiccups. Stumbling forward, "
                f"they swung wildly at shifting shadows and flagstones, yet miraculously pulled off accidental heroic feats "
                f"when a misplaced stumble tripped an encroaching foe."
            )

        if "foolishness" in penalties_norm:
            narrative_parts.append(
                f"Seized by unfathomable 'foolishness', {character_name} mistook a snarling goblin sentry for a goblin-shaped coat rack, "
                f"offering friendly criticism of its craftsmanship before casually hanging a wet cloak over its ears. "
                f"Ignoring all conventional tactical cover, they boldly strolled through the danger zone, turning mortal danger into pure farce."
            )

        if "greed" in penalties_norm:
            narrative_parts.append(
                f"Blinded by brazen 'greed', {character_name} prioritized treasure over survival, aggressively looting "
                f"every tarnished urn and stuffing several suspicious, faintly-glowing cursed copper coins into their pouches "
                f"while comrades desperately parried steel inches from their ears."
            )

        if "cowardice" in penalties_norm:
            narrative_parts.append(
                f"Overcome by sudden 'cowardice', {character_name} displayed Olympic-level evasion gymnastics, treating the nearest "
                f"stone pillar—and occasionally a bewildered halfling companion—as absolute tactical cover while loudly claiming "
                f"to be 'securing the perimeter from tactical retreat vectors'."
            )

        if not penalties_norm:
            narrative_parts.append(
                f"{character_name} conducted themselves with steadfast determination, holding the battle line with unwavering discipline "
                f"and maintaining party formations without succumbing to chaotic misadventures."
            )

        # Health & loot status narrative
        if hp_delta < 0:
            narrative_parts.append(
                f"The ordeal took a physical toll: {character_name} suffered {abs(hp_delta)} damage (scrapes, bruises, and dignity), "
                f"though they stubbornly insisted each blow was merely an unconventional defensive feint."
            )
        elif hp_delta > 0:
            narrative_parts.append(
                f"Curiously, {character_name} emerged {hp_delta} HP healthier than when you departed, having apparently quaffed "
                f"a draught of suspicious restorative nectar found in an unlabelled flask."
            )
        else:
            narrative_parts.append(
                f"Miraculously, {character_name} emerged with hit points intact and all vital organs situated where they belong."
            )

        if items_list:
            items_str = ", ".join(items_list)
            narrative_parts.append(
                f"Their pockets are heavier today: {character_name} managed to acquire {items_str}."
            )

        narrative_parts.append(
            f"Take up your dice, {character_name}. Your companions survived, and your legend—for better or worse—has grown."
        )

        full_narrative = " ".join(narrative_parts)

        # Extract or generate highlights
        highlights = self._extract_highlights(
            character_name=character_name,
            persona=persona_norm,
            penalties=penalties_norm,
            actions=actions_list,
            hp_delta=hp_delta,
            items_acquired=items_list,
        )

        aggregate_uuid = _to_uuid(session_id)

        return AbsenteeRecapGenerated(
            aggregate_id=aggregate_uuid,
            session_id=session_id,
            character_id=character_id,
            character_name=character_name,
            stand_in_persona=stand_in_persona,
            penalties=penalties,
            narrative_summary=full_narrative,
            highlights=highlights,
            audio_url=audio_url,
            hp_delta=hp_delta,
            items_acquired=items_list,
        )

    def _extract_highlights(
        self,
        character_name: str,
        persona: str,
        penalties: list[str],
        actions: list[dict[str, Any]],
        hp_delta: int,
        items_acquired: list[str],
    ) -> list[str]:
        """Synthesize 3-5 punchy highlight bullets from session actions and penalties."""
        highlights: list[str] = []

        # Parse actions if passed
        for act in actions:
            desc = (
                act.get("action_description")
                or act.get("flavor_text")
                or act.get("details")
                or act.get("narrative_flavor")
            )
            dlg = act.get("dialogue")
            if desc:
                bullet = desc
                if dlg:
                    bullet += f' (Shouted: "{dlg}")'
                highlights.append(bullet)
            if len(highlights) >= 3:
                break

        # If highlights are sparse, synthesize from penalties and persona
        if "drunk" in penalties:
            highlights.append(
                f"{character_name} swayed unsteadily through combat, slurring battlecries and hiccuping past enemy spears."
            )
            highlights.append(
                "Accidental stumble resulted in knocking an enemy off balance with a stray tankard."
            )

        if "foolishness" in penalties:
            highlights.append(
                "Mistook a snarling goblin for a coat rack and casually draped equipment over it."
            )
            highlights.append(
                "Ignored all tactical cover to give a loud lecture on defensive geometry mid-skirmish."
            )

        if "greed" in penalties:
            highlights.append(
                "Disengaged from combat to loot shiny copper coins from a suspiciously cursed urn."
            )

        if "cowardice" in penalties:
            highlights.append(
                "Expertly utilized a stone pillar and a teammate as total cover against ranged volleys."
            )

        if not penalties and not highlights:
            highlights.append(
                f"{character_name} held the vanguard with textbook discipline, protecting party spellcasters."
            )
            highlights.append(
                f"Coordinated tactical flanking maneuvers under the '{persona}' persona."
            )

        if items_acquired:
            highlights.append(f"Secured loot: {', '.join(items_acquired)}.")

        if hp_delta != 0:
            delta_str = f"{hp_delta:+d} HP"
            highlights.append(f"Health change during absence: {delta_str}.")

        # Deduplicate and limit to 4 highlights
        deduped: list[str] = []
        for h in highlights:
            if h not in deduped:
                deduped.append(h)
            if len(deduped) >= 4:
                break

        return deduped
