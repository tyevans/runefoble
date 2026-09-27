"""Service coordinator for executing turf war skirmishes and unrest state mutation."""

from __future__ import annotations

import logging
from typing import Any

from the_watcher.dependencies import (
    STREAM_WORLD,
    get_event_bus,
    get_regional_unrest_repo,
    to_uuid,
)
from the_watcher.turf_war.aggregate import RegionalUnrestAggregate
from the_watcher.turf_war.models import (
    SkirmishSimulateRequest,
    SkirmishSimulateResponse,
)
from the_watcher.turf_war.skirmish_engine import skirmish_engine
from the_watcher.turf_war.unrest_calculator import unrest_calculator

logger = logging.getLogger("runefoble.the_watcher.turf_war.service")


async def load_or_create_unrest(region_id: str, campaign_id: str = "") -> RegionalUnrestAggregate:
    """Load or instantiate an event-sourced RegionalUnrestAggregate."""
    repo = get_regional_unrest_repo()
    agg_uuid = to_uuid(region_id)
    try:
        return await repo.load(agg_uuid)
    except Exception:
        agg = RegionalUnrestAggregate(aggregate_id=agg_uuid)
        agg.state.region_id = region_id
        if campaign_id:
            agg.state.campaign_id = campaign_id
        return agg


async def publish_turf_events(events: list[Any]) -> None:
    """Fan out domain events to the world stream."""
    bus = get_event_bus()
    if not bus:
        return
    for evt in events:
        try:
            if hasattr(bus, "publish_event"):
                await bus.publish_event(STREAM_WORLD, evt)
            elif hasattr(bus, "publish"):
                await bus.publish(STREAM_WORLD, evt)
        except Exception as e:
            logger.warning("Failed to publish event to stream %s: %s", STREAM_WORLD, e)


async def execute_skirmish_simulation(
    req: SkirmishSimulateRequest,
) -> SkirmishSimulateResponse:
    """Orchestrate skirmish resolution, mutate aggregate state, and fan out events."""
    agg = await load_or_create_unrest(req.region_id, req.campaign_id)
    outcome = skirmish_engine.resolve(req)

    agg.record_skirmish(
        skirmish_id=outcome.skirmish_id,
        attacker_faction_id=req.attacker.faction_id,
        defender_faction_id=req.defender.faction_id,
        winning_faction_id=outcome.winner_faction_id,
        contested_node=req.contested_node,
        attacker_casualties=outcome.attacker_casualties,
        defender_casualties=outcome.defender_casualties,
        territory_captured=outcome.territory_captured,
        unrest_delta=outcome.unrest_delta,
        narrative=outcome.narrative,
        is_stalemate=outcome.is_stalemate,
        campaign_id=req.campaign_id,
        metadata=req.metadata,
    )

    controlling_faction = agg.state.controlling_faction_id or req.defender.faction_id
    if outcome.territory_captured:
        controlling_faction = outcome.winner_faction_id
        agg.capture_territory(
            new_controlling_faction_id=outcome.winner_faction_id,
            territory_node=req.contested_node,
            unrest_delta=outcome.unrest_delta,
            campaign_id=req.campaign_id,
            metadata=req.metadata,
        )

    new_unrest, alert, sec, friction = unrest_calculator.calculate_escalation(
        agg.state.unrest_score, outcome.unrest_delta
    )
    agg.escalate_unrest(
        current_unrest=new_unrest,
        unrest_delta=outcome.unrest_delta,
        alert_level=alert,
        security_level=sec,
        economic_friction=friction,
        cause=f"Skirmish between {req.attacker.faction_id} and {req.defender.faction_id} at {req.contested_node}",
        campaign_id=req.campaign_id,
        metadata=req.metadata,
    )

    uncommitted = list(agg.uncommitted_events)
    await get_regional_unrest_repo().save(agg)
    await publish_turf_events(uncommitted)

    return SkirmishSimulateResponse(
        skirmish_id=outcome.skirmish_id,
        campaign_id=req.campaign_id,
        region_id=req.region_id,
        contested_node=req.contested_node,
        winner_faction_id=outcome.winner_faction_id,
        loser_faction_id=outcome.loser_faction_id,
        is_stalemate=outcome.is_stalemate,
        territory_captured=outcome.territory_captured,
        controlling_faction_id=controlling_faction,
        attacker_casualties=outcome.attacker_casualties,
        defender_casualties=outcome.defender_casualties,
        unrest_delta=outcome.unrest_delta,
        current_unrest=new_unrest,
        alert_level=alert,
        security_level=sec,
        economic_friction=friction,
        narrative=outcome.narrative,
    )
