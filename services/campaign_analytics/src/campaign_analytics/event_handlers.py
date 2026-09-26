"""Event projection dispatcher and domain event handlers for campaign analytics.

Governed by: ADR-0003, ADR-0006, ADR-0011.
"""

from __future__ import annotations

from typing import Any

from campaign_analytics.event_helpers import get_event_attr, is_event_type
from campaign_analytics.storage import CampaignAnalyticsStorage

__all__ = [
    "AnalyticsEventDispatcher",
    "get_event_attr",
    "handle_domain_event",
    "is_event_type",
]


class AnalyticsEventDispatcher:
    """Dispatches domain events to analytical projections with ephemeral spatial tracking."""

    def __init__(self, storage: CampaignAnalyticsStorage) -> None:
        self.storage = storage
        self.token_positions: dict[str, tuple[int, int]] = {}
        self.token_names: dict[str, str] = {}
        self.active_combatants: dict[str, str] = {}
        self.active_encounters: dict[str, str] = {}

    def extract_context(self, event: Any) -> tuple[str, str]:
        """Extract session_id and campaign_id from the incoming event."""
        sid = str(
            get_event_attr(event, "session_id") or get_event_attr(event, "aggregate_id") or ""
        )
        raw_c = get_event_attr(event, "campaign_id") or get_event_attr(event, "campaign_id_str")
        cid = str(raw_c) if raw_c else self.storage.resolve_campaign_id(sid)
        return sid, cid

    async def _milestone(
        self, sid: str, cid: str, m: str, t: str, d: str, meta: Any = None
    ) -> None:
        await self.storage.record_milestone(cid or sid, sid, m, t, d, metadata_dict=meta)

    async def _stat(self, sid: str, cid: str, actor: str, name: str, **kwargs: Any) -> None:
        enc = self.active_encounters.get(sid, "default")
        await self.storage.record_combatant_stat(cid or sid, sid, enc, actor, name, **kwargs)

    async def _spatial(
        self, sid: str, cid: str, tok: str, n: str, x: int, y: int, e: str, **kw: Any
    ) -> None:
        await self.storage.record_spatial(cid or sid, sid, tok, n, x, y, e, **kw)

    async def handle_session_lifecycle(self, event: Any, sid: str, cid: str) -> bool:
        """Handle SessionCreated, SessionStarted, and SessionEnded milestones."""
        if is_event_type(event, ["SessionCreated", "runefoble.events.session.created"]):
            title = str(get_event_attr(event, "title", "Untitled Session"))
            if (nc := str(get_event_attr(event, "campaign_id", ""))) and sid:
                self.storage.map_session(sid, nc)
                cid = nc
            await self._milestone(
                sid,
                cid,
                "session_start",
                f"Session Created: {title}",
                f"Campaign session '{title}' created.",
                {"title": title},
            )
            return True
        if is_event_type(event, ["SessionStarted", "GameSessionStarted"]):
            desc = "The party assembled and the session officially commenced."
            await self._milestone(sid, cid, "session_start", "Session Began", desc)
            return True
        if is_event_type(event, ["SessionEnded", "runefoble.events.session.ended"]):
            s = str(get_event_attr(event, "summary", "Session concluded"))
            await self._milestone(sid, cid, "session_end", "Session Concluded", s, {"summary": s})
            return True
        return False

    async def handle_spatial(self, event: Any, sid: str, cid: str) -> bool:
        """Handle token placement and movement events."""
        is_p = is_event_type(event, ["TokenPlaced"])
        is_m = is_event_type(event, ["TokenMoved", "BoardMoveEvent"])
        if not (is_p or is_m):
            return False
        tok, name = (
            str(get_event_attr(event, "token_id", "")),
            str(get_event_attr(event, "name", "Token")),
        )
        x, y = (
            int(get_event_attr(event, "to_x" if is_m else "x", 0)),
            int(get_event_attr(event, "to_y" if is_m else "y", 0)),
        )
        if tok:
            self.token_positions[tok], self.token_names[tok] = (x, y), name
        await self._spatial(sid, cid, tok, name, x, y, "movement")
        return True

    async def handle_character_health(self, event: Any, sid: str, cid: str) -> bool:
        """Handle damage, healing, knockout milestones, and combatant efficacy."""
        if not is_event_type(event, ["CharacterHealthChanged"]):
            return False
        char_id = str(get_event_attr(event, "aggregate_id", ""))
        delta = int(get_event_attr(event, "delta", 0))
        curr_hp = int(get_event_attr(event, "current_hp", 0))
        dealer = get_event_attr(event, "dealer_id")
        actor = str(dealer or self.active_combatants.get(sid) or char_id)
        pos, cname = (
            self.token_positions.get(char_id, (0, 0)),
            self.token_names.get(char_id, char_id),
        )
        aname = self.token_names.get(actor, actor)
        if delta < 0:
            dmg = abs(delta)
            await self._stat(sid, cid, char_id, cname, damage_taken=dmg)
            if actor and actor != char_id:
                await self._stat(sid, cid, actor, aname, damage_dealt=dmg)
            await self._spatial(sid, cid, char_id, cname, pos[0], pos[1], "damage", damage=dmg)
            if curr_hp <= 0:
                await self._spatial(sid, cid, char_id, cname, pos[0], pos[1], "knockout")
                desc = f"{cname} took lethal damage and fell to 0 HP at coordinates ({pos[0]}, {pos[1]})."
                meta = {"character_id": char_id, "coordinates": list(pos)}
                await self._milestone(
                    sid, cid, "character_knockout", f"{cname} Knocked Unconscious", desc, meta
                )
        elif delta > 0:
            await self._stat(sid, cid, actor, aname, healing_provided=delta)
        return True

    async def handle_dice(self, event: Any, sid: str, cid: str) -> bool:
        """Handle dice rolls, critical strikes, and fumbles."""
        if not is_event_type(
            event, ["DiceRolled", "DiceRollEvent", "runefoble.events.dice.rolled"]
        ):
            return False
        rid = str(get_event_attr(event, "roller_id", "roller"))
        rname = str(get_event_attr(event, "roller_name", rid))
        if rid and rname:
            self.token_names[rid] = rname
        formula = str(get_event_attr(event, "formula", "1d20"))
        total = int(get_event_attr(event, "total", 0))
        crit = bool(get_event_attr(event, "is_crit", False))
        fumble = bool(get_event_attr(event, "is_fumble", False))
        await self._stat(sid, cid, rid, rname, critical_hits=int(crit), fumbles=int(fumble))
        if crit:
            desc = f"{rname} rolled a natural critical ({total}) on {formula}."
            meta = {"roller_id": rid, "formula": formula, "total": total}
            await self._milestone(
                sid, cid, "critical_moment", f"Critical Strike by {rname}!", desc, meta
            )
        return True

    async def handle_combat(self, event: Any, sid: str, cid: str) -> bool:
        """Handle combat round progression and encounter initialization."""
        if is_event_type(event, ["CombatRoundAdvanced"]):
            rnd = int(get_event_attr(event, "round_number", 1))
            active_id = str(get_event_attr(event, "active_combatant_id", ""))
            if active_id and sid:
                self.active_combatants[sid] = active_id
                aname = self.token_names.get(active_id, active_id)
                await self._stat(sid, cid, active_id, aname, turns_taken=1)
            desc = f"Encounter advanced to round {rnd}."
            meta = {"round_number": rnd, "active_combatant_id": active_id}
            await self._milestone(sid, cid, "combat_round", f"Combat Round {rnd}", desc, meta)
            return True
        types = [
            "CombatEncounterStarted",
            "CombatStarted",
            "EncounterSpawned",
            "runefoble.events.encounter.spawned",
        ]
        if is_event_type(event, types):
            raw = get_event_attr(event, "encounter_name") or get_event_attr(event, "name")
            name = str(raw or "Combat")
            enc_id = str(get_event_attr(event, "encounter_id", "enc_1"))
            if sid:
                self.active_encounters[sid] = enc_id
            t = f"Encounter Initiated: {name}"
            meta = {"encounter_id": enc_id, "name": name}
            await self._milestone(
                sid, cid, "boss_encounter", t, f"Tactical encounter '{name}' commenced.", meta
            )
            return True
        return False

    async def handle_recap(self, event: Any, sid: str, cid: str) -> bool:
        """Handle absentee chronicle recaps."""
        if not is_event_type(event, ["AbsenteeRecapGenerated", "runefoble.events.recap.generated"]):
            return False
        cname = str(get_event_attr(event, "character_name", "Adventurer"))
        narrative = str(get_event_attr(event, "narrative_summary", ""))
        desc = narrative or f"Session recap recorded for {cname}."
        meta = {"character_name": cname}
        await self._milestone(sid, cid, "recap", f"Chronicle Recap: {cname}", desc, meta)
        return True

    async def dispatch(self, event: Any) -> None:
        """Dispatch a single domain event across projection handlers."""
        sid, cid = self.extract_context(event)
        for h in (
            self.handle_session_lifecycle,
            self.handle_spatial,
            self.handle_character_health,
            self.handle_dice,
            self.handle_combat,
            self.handle_recap,
        ):
            if await h(event, sid, cid):
                return


async def handle_domain_event(
    event: Any,
    storage: CampaignAnalyticsStorage,
    dispatcher: AnalyticsEventDispatcher | None = None,
) -> None:
    """Project domain event into analytics storage using an event dispatcher."""
    target = dispatcher or AnalyticsEventDispatcher(storage)
    await target.dispatch(event)
