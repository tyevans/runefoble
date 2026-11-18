"""Domain event projection handlers for campaign analytics.

Milestones are recorded through CampaignChronicleAggregate and the event store, then projected
into the milestone read model. Every other write goes to the read-model tables. Per-token and
per-session context lives in projection state, so a restart resumes with the same context.

Governed by: ADR-0003, ADR-0006, ADR-0011, Hard Invariant 2.
"""

from __future__ import annotations

from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from eventsource.application.aggregates.repository import AggregateRepository

from campaign_analytics.aggregate import CampaignChronicleAggregate
from campaign_analytics.event_helpers import get_event_attr, is_event_type
from campaign_analytics.projection import (
    ACTIVE_COMBATANT_SCOPE,
    ACTIVE_ENCOUNTER_SCOPE,
    TOKEN_NAME_SCOPE,
    TOKEN_POSITION_SCOPE,
    ProjectionTx,
)

__all__ = [
    "AnalyticsEventDispatcher",
    "chronicle_aggregate_id",
    "get_event_attr",
    "is_event_type",
]


def chronicle_aggregate_id(campaign_id: str) -> UUID:
    """Return the stable chronicle aggregate id for a campaign."""
    return uuid5(NAMESPACE_URL, f"runefoble:campaign-chronicle:{campaign_id}")


class AnalyticsEventDispatcher:
    """Dispatches domain events to analytical projections inside one projection transaction."""

    def __init__(self, chronicle: AggregateRepository[CampaignChronicleAggregate]) -> None:
        self.chronicle = chronicle

    async def extract_context(self, event: Any, tx: ProjectionTx) -> tuple[str, str]:
        """Extract session_id and campaign_id from the incoming event."""
        sid = str(
            get_event_attr(event, "session_id") or get_event_attr(event, "aggregate_id") or ""
        )
        raw_c = get_event_attr(event, "campaign_id") or get_event_attr(event, "campaign_id_str")
        cid = str(raw_c) if raw_c else await tx.resolve_campaign(sid)
        return sid, cid

    async def _milestone(
        self,
        tx: ProjectionTx,
        sid: str,
        cid: str,
        milestone_type: str,
        title: str,
        description: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        """Record the milestone on the chronicle aggregate, then project the saved event."""
        campaign = cid or sid
        metadata = meta or {}
        aggregate = await self.chronicle.load_or_create(chronicle_aggregate_id(campaign))
        aggregate.record_milestone(
            campaign_id=campaign,
            session_id=sid,
            milestone_type=milestone_type,
            title=title,
            description=description,
            metadata=metadata,
        )
        recorded = list(aggregate.uncommitted_events)[-1]
        await self.chronicle.save(aggregate)
        await tx.add_milestone(
            campaign,
            sid,
            milestone_type,
            title,
            description,
            recorded.occurred_at.isoformat(),
            metadata,
        )

    async def _stat(
        self, tx: ProjectionTx, sid: str, cid: str, actor: str, name: str, **kwargs: int
    ) -> None:
        enc = await tx.get_state(ACTIVE_ENCOUNTER_SCOPE, sid, "default")
        await tx.add_combatant_stat(cid or sid, sid, enc, actor, name, **kwargs)

    async def _spatial(
        self,
        tx: ProjectionTx,
        sid: str,
        cid: str,
        tok: str,
        name: str,
        x: int,
        y: int,
        event_type: str,
        damage: int = 0,
    ) -> None:
        await tx.add_spatial(cid or sid, sid, tok, name, x, y, event_type, damage)

    async def handle_session_lifecycle(
        self, event: Any, tx: ProjectionTx, sid: str, cid: str
    ) -> bool:
        """Handle SessionCreated, SessionStarted, and SessionEnded milestones."""
        if is_event_type(event, ["SessionCreated", "runefoble.events.session.created"]):
            title = str(get_event_attr(event, "title", "Untitled Session"))
            if (nc := str(get_event_attr(event, "campaign_id", ""))) and sid:
                await tx.map_session(sid, nc)
                cid = nc
            await self._milestone(
                tx,
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
            await self._milestone(tx, sid, cid, "session_start", "Session Began", desc)
            return True
        if is_event_type(event, ["SessionEnded", "runefoble.events.session.ended"]):
            s = str(get_event_attr(event, "summary", "Session concluded"))
            await self._milestone(
                tx, sid, cid, "session_end", "Session Concluded", s, {"summary": s}
            )
            return True
        return False

    async def handle_spatial(self, event: Any, tx: ProjectionTx, sid: str, cid: str) -> bool:
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
            await tx.set_state(TOKEN_POSITION_SCOPE, tok, [x, y])
            await tx.set_state(TOKEN_NAME_SCOPE, tok, name)
        await self._spatial(tx, sid, cid, tok, name, x, y, "movement")
        return True

    async def handle_character_health(
        self, event: Any, tx: ProjectionTx, sid: str, cid: str
    ) -> bool:
        """Handle damage, healing, knockout milestones, and combatant efficacy."""
        if not is_event_type(event, ["CharacterHealthChanged"]):
            return False
        char_id = str(get_event_attr(event, "aggregate_id", ""))
        delta = int(get_event_attr(event, "delta", 0))
        curr_hp = int(get_event_attr(event, "current_hp", 0))
        dealer = get_event_attr(event, "dealer_id")
        active = await tx.get_state(ACTIVE_COMBATANT_SCOPE, sid)
        actor = str(dealer or active or char_id)
        pos = await tx.get_state(TOKEN_POSITION_SCOPE, char_id, [0, 0])
        cname = await tx.get_state(TOKEN_NAME_SCOPE, char_id, char_id)
        aname = await tx.get_state(TOKEN_NAME_SCOPE, actor, actor)
        if delta < 0:
            dmg = abs(delta)
            await self._stat(tx, sid, cid, char_id, cname, damage_taken=dmg)
            if actor and actor != char_id:
                await self._stat(tx, sid, cid, actor, aname, damage_dealt=dmg)
            await self._spatial(tx, sid, cid, char_id, cname, pos[0], pos[1], "damage", dmg)
            if curr_hp <= 0:
                await self._spatial(tx, sid, cid, char_id, cname, pos[0], pos[1], "knockout")
                desc = f"{cname} took lethal damage and fell to 0 HP at coordinates ({pos[0]}, {pos[1]})."
                meta = {"character_id": char_id, "coordinates": list(pos)}
                await self._milestone(
                    tx,
                    sid,
                    cid,
                    "character_knockout",
                    f"{cname} Knocked Unconscious",
                    desc,
                    meta,
                )
        elif delta > 0:
            await self._stat(tx, sid, cid, actor, aname, healing_provided=delta)
        return True

    async def handle_dice(self, event: Any, tx: ProjectionTx, sid: str, cid: str) -> bool:
        """Handle dice rolls, critical strikes, and fumbles."""
        if not is_event_type(
            event, ["DiceRolled", "DiceRollEvent", "runefoble.events.dice.rolled"]
        ):
            return False
        rid = str(get_event_attr(event, "roller_id", "roller"))
        rname = str(get_event_attr(event, "roller_name", rid))
        if rid and rname:
            await tx.set_state(TOKEN_NAME_SCOPE, rid, rname)
        formula = str(get_event_attr(event, "formula", "1d20"))
        total = int(get_event_attr(event, "total", 0))
        crit = bool(get_event_attr(event, "is_crit", False))
        fumble = bool(get_event_attr(event, "is_fumble", False))
        await self._stat(tx, sid, cid, rid, rname, critical_hits=int(crit), fumbles=int(fumble))
        if crit:
            desc = f"{rname} rolled a natural critical ({total}) on {formula}."
            meta = {"roller_id": rid, "formula": formula, "total": total}
            await self._milestone(
                tx, sid, cid, "critical_moment", f"Critical Strike by {rname}!", desc, meta
            )
        return True

    async def handle_combat(self, event: Any, tx: ProjectionTx, sid: str, cid: str) -> bool:
        """Handle combat round progression and encounter initialization."""
        if is_event_type(event, ["CombatRoundAdvanced"]):
            rnd = int(get_event_attr(event, "round_number", 1))
            active_id = str(get_event_attr(event, "active_combatant_id", ""))
            if active_id and sid:
                await tx.set_state(ACTIVE_COMBATANT_SCOPE, sid, active_id)
                aname = await tx.get_state(TOKEN_NAME_SCOPE, active_id, active_id)
                await self._stat(tx, sid, cid, active_id, aname, turns_taken=1)
            desc = f"Encounter advanced to round {rnd}."
            meta = {"round_number": rnd, "active_combatant_id": active_id}
            await self._milestone(tx, sid, cid, "combat_round", f"Combat Round {rnd}", desc, meta)
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
                await tx.set_state(ACTIVE_ENCOUNTER_SCOPE, sid, enc_id)
            t = f"Encounter Initiated: {name}"
            meta = {"encounter_id": enc_id, "name": name}
            await self._milestone(
                tx, sid, cid, "boss_encounter", t, f"Tactical encounter '{name}' commenced.", meta
            )
            return True
        return False

    async def handle_recap(self, event: Any, tx: ProjectionTx, sid: str, cid: str) -> bool:
        """Handle absentee chronicle recaps."""
        if not is_event_type(event, ["AbsenteeRecapGenerated", "runefoble.events.recap.generated"]):
            return False
        cname = str(get_event_attr(event, "character_name", "Adventurer"))
        narrative = str(get_event_attr(event, "narrative_summary", ""))
        desc = narrative or f"Session recap recorded for {cname}."
        meta = {"character_name": cname}
        await self._milestone(tx, sid, cid, "recap", f"Chronicle Recap: {cname}", desc, meta)
        return True

    async def dispatch(self, event: Any, tx: ProjectionTx) -> None:
        """Dispatch a single domain event across projection handlers."""
        sid, cid = await self.extract_context(event, tx)
        for h in (
            self.handle_session_lifecycle,
            self.handle_spatial,
            self.handle_character_health,
            self.handle_dice,
            self.handle_combat,
            self.handle_recap,
        ):
            if await h(event, tx, sid, cid):
                return
