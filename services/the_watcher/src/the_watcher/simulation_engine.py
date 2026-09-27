"""Background simulation engine for autonomous NPC faction agendas and world ticks.

Governed by:
- ADR-0002: Event-Driven Watcher Gameplay Orchestration
- ADR-0006: Redis Streams Event Bus
- ADR-0011: eventsource-py Core Event Sourcing
"""

from __future__ import annotations

import contextlib
import datetime
import random
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

from runefoble_events.watcher import WorldTickExecuted
from the_watcher.bulletin import build_intelligence_bulletin, generate_geopolitical_shift
from the_watcher.faction_models import (
    FactionResponse,
    GeopoliticalShiftModel,
    WorldTickRequest,
    WorldTickResponse,
)
from the_watcher.factions import FactionAggregate

STREAM_WATCHER = "runefoble.events.watcher"


def to_uuid(val: str | UUID | None) -> UUID:
    if val is None:
        return uuid4()
    if isinstance(val, UUID):
        return val
    try:
        return UUID(val)
    except ValueError:
        return uuid5(NAMESPACE_DNS, str(val))


class FactionSimulationEngine:
    """Simulates background faction agenda progression, rival clashes, and intelligence briefs."""

    def __init__(self) -> None:
        self._campaign_factions: dict[str, list[str]] = {}
        self._campaign_ticks: dict[str, int] = {}
        self._latest_bulletins: dict[str, WorldTickResponse] = {}

    def register_faction_id(self, campaign_id: str, faction_id: str) -> None:
        """Track faction ID under a campaign."""
        factions = self._campaign_factions.setdefault(campaign_id, [])
        if faction_id not in factions:
            factions.append(faction_id)

    def get_campaign_faction_ids(self, campaign_id: str) -> list[str]:
        return list(self._campaign_factions.get(campaign_id, []))

    def clear(self) -> None:
        self._campaign_factions.clear()
        self._campaign_ticks.clear()
        self._latest_bulletins.clear()

    async def ensure_default_factions(self, campaign_id: str, repo: Any) -> list[FactionAggregate]:
        """Seed canonical default factions if none are currently registered for the campaign."""
        existing_ids = self.get_campaign_faction_ids(campaign_id)
        aggregates: list[FactionAggregate] = []
        if existing_ids:
            for fid in existing_ids:
                try:
                    agg = await repo.load(to_uuid(fid))
                    aggregates.append(agg)
                except Exception:
                    pass
            if aggregates:
                return aggregates

        defaults = [
            {
                "name": "Ironfang Syndicate",
                "influence": 60,
                "resources": 55,
                "disposition": "hostile",
                "active_goal": "Smuggle Arcane Weapons into Oakhaven",
                "territory": "Oakhaven Docks",
                "rivals": ["Silver Dawn Guild"],
            },
            {
                "name": "Arcane Order",
                "influence": 70,
                "resources": 65,
                "disposition": "neutral",
                "active_goal": "Infiltrate Arcane Guild Archives",
                "territory": "High Spire",
                "rivals": ["Ironfang Syndicate"],
            },
            {
                "name": "Silver Dawn Guild",
                "influence": 50,
                "resources": 45,
                "disposition": "friendly",
                "active_goal": "Patrol Eastern Trade Outpost",
                "territory": "Oakhaven Outpost",
                "rivals": ["Ironfang Syndicate"],
            },
        ]

        created_aggs: list[FactionAggregate] = []
        for d in defaults:
            fid = f"faction-{uuid4().hex[:8]}"
            agg = FactionAggregate(aggregate_id=to_uuid(fid))
            agg.initialize(
                campaign_id=campaign_id,
                faction_id=fid,
                name=d["name"],
                influence=d["influence"],
                resources=d["resources"],
                disposition=d["disposition"],
                active_goal=d["active_goal"],
                rival_faction_ids=d.get("rivals", []),
                territory=d["territory"],
            )
            await repo.save(agg)
            self.register_faction_id(campaign_id, fid)
            created_aggs.append(agg)
        return created_aggs

    def _resolve_check(
        self,
        faction: FactionAggregate,
        all_factions: list[FactionAggregate],
        stability: int,
        rng: random.Random,
    ) -> tuple[int, int, int, str, int, str]:
        """Probabilistically resolve a faction's agenda roll against rival counter-measures."""
        state = faction.state
        subversive = any(
            w in state.active_goal.lower()
            for w in ["smuggle", "infiltrate", "assassinate", "sabotage", "corrupt", "steal"]
        )

        rival_defense = 0
        for other in all_factions:
            if other.state.faction_id != state.faction_id and (
                other.state.faction_id in state.rival_faction_ids
                or state.faction_id in other.state.rival_faction_ids
            ):
                rival_defense = max(rival_defense, other.state.influence)

        base_dc = 13
        stability_mod = (stability - 50) // 10
        rival_mod = rival_defense // 20
        dc = base_dc + (stability_mod if subversive else -stability_mod) + rival_mod
        dc = max(8, min(22, dc))

        roll = rng.randint(1, 20)
        modifier = (state.influence // 10) + (state.resources // 20)
        total = roll + modifier

        if roll == 20 or total >= dc + 5:
            outcome = "success"
            delta = 35
            narrative = f"{state.name} executed a decisive stroke for '{state.active_goal}'."
        elif total >= dc:
            outcome = "success"
            delta = 25
            narrative = f"{state.name} made steady progress advancing '{state.active_goal}'."
        elif total >= dc - 4:
            outcome = "partial_success"
            delta = 10
            narrative = f"{state.name} achieved incremental progress on '{state.active_goal}'."
        elif rival_defense >= 55 and total < dc - 4:
            outcome = "countered"
            delta = -10
            narrative = f"{state.name}'s agents were intercepted and ambushed by rivals."
        else:
            outcome = "failure"
            delta = 0
            narrative = f"{state.name}'s operation for '{state.active_goal}' stalled."

        return roll, modifier, dc, outcome, delta, narrative

    async def execute_world_tick(
        self,
        campaign_id: str,
        req: WorldTickRequest,
        repo: Any,
        bus: Any = None,
    ) -> WorldTickResponse:
        """Advance faction agendas, resolve rolls, persist events, and generate intelligence."""
        rng = random.Random(req.random_seed) if req.random_seed is not None else random.Random()

        factions = await self.ensure_default_factions(campaign_id, repo)
        tick_num = self._campaign_ticks.get(campaign_id, 0) + req.ticks
        self._campaign_ticks[campaign_id] = tick_num

        shifts: list[GeopoliticalShiftModel] = []
        rumors: list[str] = list(req.custom_rumors or [])
        faction_summaries: list[FactionResponse] = []

        for f in factions:
            roll, mod, dc, outcome, delta, narrative = self._resolve_check(
                f, factions, req.regional_stability, rng
            )
            f.advance_agenda(
                agenda_name=f.state.active_goal,
                roll=roll,
                modifier=mod,
                dc=dc,
                outcome=outcome,
                progress_delta=delta,
                narrative=narrative,
            )

            # Check if agenda reached completion target (triggers shift)
            if f.state.goal_progress >= f.state.goal_target:
                terr = f.state.territory or "Strategic Sector"
                s_type, desc, sev, effects = generate_geopolitical_shift(f, terr)
                f.record_shift(
                    territory=terr,
                    shift_type=s_type,
                    description=desc,
                    severity=sev,
                    ripple_effects=effects,
                )
                shifts.append(
                    GeopoliticalShiftModel(
                        faction_id=f.state.faction_id,
                        faction_name=f.state.name,
                        territory=terr,
                        shift_type=s_type,
                        description=desc,
                        severity=sev,
                        ripple_effects=effects,
                    )
                )
                rumors.append(
                    f"Overheard at tavern: '{desc} Watch yourself if you head toward {terr}.'"
                )
                f.set_agenda(active_goal=f"Consolidate dominance in {terr}", target_progress=100)
            elif outcome in ("success", "critical_success"):
                rumors.append(
                    f"Tavern gossip: '{f.state.name} agents were active around {f.state.territory}.'"
                )
            elif outcome == "countered":
                rumors.append(
                    f"Street rumor: 'Skirmish in the alleys! {f.state.name} took a beating from rivals.'"
                )

            await repo.save(f)
            faction_summaries.append(
                FactionResponse(
                    faction_id=f.state.faction_id,
                    campaign_id=f.state.campaign_id,
                    name=f.state.name,
                    influence=f.state.influence,
                    resources=f.state.resources,
                    disposition=f.state.disposition,
                    active_goal=f.state.active_goal,
                    goal_progress=f.state.goal_progress,
                    goal_target=f.state.goal_target,
                    rival_faction_ids=f.state.rival_faction_ids,
                    territory=f.state.territory,
                    shifts=f.state.shifts,
                    history=f.state.history,
                )
            )

        if not rumors:
            rumors.append("Quiet whispers circulate that tensions are simmering under the surface.")

        bulletin = build_intelligence_bulletin(
            campaign_id, tick_num, req.regional_stability, faction_summaries, shifts, rumors
        )
        now_iso = datetime.datetime.now(datetime.UTC).isoformat()

        tick_event = WorldTickExecuted(
            campaign_id=campaign_id,
            tick_number=tick_num,
            intelligence_bulletin=bulletin,
            factions_simulated=[f.state.faction_id for f in factions],
            shifts=[s.model_dump() for s in shifts],
            rumors=rumors,
        )
        if bus is not None:
            with contextlib.suppress(Exception):
                await bus.publish(STREAM_WATCHER, tick_event)

        response = WorldTickResponse(
            campaign_id=campaign_id,
            tick_number=tick_num,
            intelligence_bulletin=bulletin,
            factions=faction_summaries,
            shifts=shifts,
            tavern_rumors=rumors,
            timestamp=now_iso,
        )
        self._latest_bulletins[campaign_id] = response
        return response

    def get_latest_bulletin(self, campaign_id: str) -> WorldTickResponse | None:
        return self._latest_bulletins.get(campaign_id)
