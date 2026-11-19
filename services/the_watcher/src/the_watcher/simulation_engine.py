"""Background simulation engine for autonomous NPC faction agendas and world ticks.

Governed by:
- ADR-0002: Event-Driven Watcher Gameplay Orchestration
- ADR-0006: Redis Streams Event Bus
- ADR-0011: eventsource-py Core Event Sourcing
"""

from __future__ import annotations

import random
from typing import Any
from uuid import uuid4

from runefoble_platform.dice import roll_d20
from runefoble_platform.event_publish import publish_or_fail
from runefoble_platform.identifiers import opaque_aggregate_id
from the_watcher.bulletin import build_intelligence_bulletin, generate_geopolitical_shift
from the_watcher.faction_models import (
    FactionResponse,
    GeopoliticalShiftModel,
    WorldTickRequest,
    WorldTickResponse,
)
from the_watcher.factions import FactionAggregate
from the_watcher.factions.campaign_world import CampaignWorldAggregate

STREAM_WATCHER = "runefoble.events.watcher"

DEFAULT_FACTIONS: list[dict[str, Any]] = [
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


def summarize_faction(faction: FactionAggregate) -> FactionResponse:
    """Build the public response model for a faction's current aggregate state."""
    state = faction.state
    return FactionResponse(
        faction_id=state.faction_id,
        campaign_id=state.campaign_id,
        name=state.name,
        influence=state.influence,
        resources=state.resources,
        disposition=state.disposition,
        active_goal=state.active_goal,
        goal_progress=state.goal_progress,
        goal_target=state.goal_target,
        rival_faction_ids=state.rival_faction_ids,
        territory=state.territory,
        shifts=state.shifts,
        history=state.history,
    )


class FactionSimulationEngine:
    """Simulates background faction agenda progression, rival clashes, and intelligence briefs.

    The engine holds no state. The campaign registry and tick counter live in
    CampaignWorldAggregate, and each faction lives in FactionAggregate. A restart therefore
    resumes the simulation from the event store.
    """

    async def register_faction(self, campaign_id: str, faction_id: str, world_repo: Any) -> None:
        """Add a faction to the campaign registry."""
        world = await world_repo.load_or_create(
            opaque_aggregate_id(campaign_id, field="campaign_id")
        )
        world.register_faction(campaign_id, faction_id)
        await world_repo.save(world)

    async def ensure_default_factions(
        self, campaign_id: str, faction_repo: Any, world_repo: Any
    ) -> list[FactionAggregate]:
        """Return the campaign's registered factions, seeding defaults when none exist."""
        _world, factions = await self._load_campaign(campaign_id, faction_repo, world_repo)
        return factions

    async def _load_campaign(
        self, campaign_id: str, faction_repo: Any, world_repo: Any
    ) -> tuple[CampaignWorldAggregate, list[FactionAggregate]]:
        world = await world_repo.load_or_create(
            opaque_aggregate_id(campaign_id, field="campaign_id")
        )
        if not world.state.faction_ids:
            await self._seed_default_factions(campaign_id, world, faction_repo, world_repo)
        factions = [
            await faction_repo.load(opaque_aggregate_id(fid, field="fid"))
            for fid in world.state.faction_ids
        ]
        return world, factions

    async def _seed_default_factions(
        self,
        campaign_id: str,
        world: CampaignWorldAggregate,
        faction_repo: Any,
        world_repo: Any,
    ) -> None:
        for d in DEFAULT_FACTIONS:
            fid = f"faction-{uuid4().hex[:8]}"
            agg = FactionAggregate(aggregate_id=opaque_aggregate_id(fid, field="fid"))
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
            await faction_repo.save(agg)
            world.register_faction(campaign_id, fid)
        await world_repo.save(world)

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

        roll = roll_d20(rng=rng)
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
        faction_repo: Any,
        world_repo: Any,
        bus: Any,
    ) -> WorldTickResponse:
        """Advance faction agendas, resolve rolls, persist state, publish, and generate intelligence."""
        rng = random.Random(req.random_seed) if req.random_seed is not None else random.Random()

        world, factions = await self._load_campaign(campaign_id, faction_repo, world_repo)
        tick_num = world.state.tick_count + req.ticks

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

            await faction_repo.save(f)
            faction_summaries.append(summarize_faction(f))

        if not rumors:
            rumors.append("Quiet whispers circulate that tensions are simmering under the surface.")

        bulletin = build_intelligence_bulletin(
            campaign_id, tick_num, req.regional_stability, faction_summaries, shifts, rumors
        )
        tick_event = world.record_world_tick(
            campaign_id=campaign_id,
            tick_number=tick_num,
            intelligence_bulletin=bulletin,
            factions_simulated=[f.state.faction_id for f in factions],
            shifts=[s.model_dump() for s in shifts],
            rumors=rumors,
        )
        await world_repo.save(world)
        await publish_or_fail(bus, STREAM_WATCHER, tick_event)

        return WorldTickResponse(
            campaign_id=campaign_id,
            tick_number=tick_num,
            intelligence_bulletin=bulletin,
            factions=faction_summaries,
            shifts=shifts,
            tavern_rumors=rumors,
            timestamp=tick_event.occurred_at.isoformat(),
        )

    async def get_latest_bulletin(
        self, campaign_id: str, faction_repo: Any, world_repo: Any
    ) -> WorldTickResponse | None:
        """Rebuild the latest world tick response from the campaign world and faction aggregates."""
        world = await world_repo.load_or_create(
            opaque_aggregate_id(campaign_id, field="campaign_id")
        )
        latest = world.state.latest_tick
        if latest is None:
            return None
        faction_summaries = [
            summarize_faction(await faction_repo.load(opaque_aggregate_id(fid, field="fid")))
            for fid in latest.factions_simulated
        ]
        return WorldTickResponse(
            campaign_id=campaign_id,
            tick_number=latest.tick_number,
            intelligence_bulletin=latest.intelligence_bulletin,
            factions=faction_summaries,
            shifts=[GeopoliticalShiftModel(**s) for s in latest.shifts],
            tavern_rumors=latest.rumors,
            timestamp=latest.timestamp,
        )
