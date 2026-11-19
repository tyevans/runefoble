"""AI Stand-in action simulation and recap routes for The Watcher service."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from runefoble_events.events import AbsencePenaltyApplied, StandInActionDecided
from runefoble_platform.event_publish import publish_or_fail
from runefoble_platform.identifiers import opaque_aggregate_id
from runefoble_platform.stand_in_action import StandInAction
from the_watcher.container_access import Engines, EventBus
from the_watcher.dependencies import STREAM_WATCHER, require_session_permission
from the_watcher.engine_selection import load_watcher_ports
from the_watcher.identity import CallerId, get_principal
from the_watcher.models import StandInRecapRequest, StandInRecapResponse, StandInRequest

router = APIRouter(dependencies=[Depends(get_principal)], tags=["stand_in"])


@router.post("/api/v1/watcher/stand-in/act", response_model=StandInAction)
async def stand_in_act(
    engines: Engines, event_bus: EventBus, caller_id: CallerId, req: StandInRequest
) -> StandInAction:
    """Simulate an action for an absent player's character with applied penalties.

    A failed engine is returned as HTTP 503. The Watcher never substitutes canned output.
    """
    await require_session_permission(caller_id, req.session_id, "session.participate")
    stand_in = await load_watcher_ports(engines.watcher).stand_in.decide(req)

    # Publish events to Redis Streams
    bus = event_bus.get()
    session_uuid = opaque_aggregate_id(req.session_id, field="session_id")
    campaign_uuid = opaque_aggregate_id(req.campaign_id, field="campaign_id")

    action_event = StandInActionDecided(
        aggregate_id=session_uuid,
        session_id=session_uuid,
        campaign_id=campaign_uuid,
        character_name=stand_in.character_name,
        action_type=stand_in.action_type,
        dialogue=stand_in.dialogue,
        penalties_applied=stand_in.penalties_applied or req.penalties,
        flavor_text=stand_in.action_description,
    )

    await publish_or_fail(bus, STREAM_WATCHER, action_event)
    for p in req.penalties:
        p_clean = p.lower()
        if p_clean in ("drunk", "foolishness", "cowardice", "greed", "curse"):
            pen_event = AbsencePenaltyApplied(
                aggregate_id=session_uuid,
                session_id=session_uuid,
                campaign_id=campaign_uuid,
                penalty_type=p_clean,
                description=stand_in.penalty_influence or f"Absence penalty {p} active",
                imposed_by="the_watcher",
            )
            await publish_or_fail(bus, STREAM_WATCHER, pen_event)

    return stand_in


@router.post("/api/v1/watcher/stand-in/recap", response_model=StandInRecapResponse)
async def stand_in_recap(
    engines: Engines, caller_id: CallerId, req: StandInRecapRequest
) -> StandInRecapResponse:
    """Generate a humorous recap of an absent player's stand-in exploits for when they return."""
    await require_session_permission(caller_id, req.session_id, "session.observe")
    data = engines.watcher.generate_stand_in_recap(
        character_name=req.character_name,
        actions=req.actions,
        penalties=req.penalties,
    )
    return StandInRecapResponse.model_validate(data)
