"""AI Stand-in action simulation and recap routes for The Watcher service."""

from __future__ import annotations

from fastapi import APIRouter
from runefoble_events.events import AbsencePenaltyApplied, StandInActionDecided
from runefoble_platform.event_publish import publish_or_fail
from the_watcher.dependencies import (
    INFERENCE_URL,
    STREAM_WATCHER,
    engine,
    get_event_bus,
    to_uuid,
)
from the_watcher.models import (
    StandInAction,
    StandInRecapRequest,
    StandInRecapResponse,
    StandInRequest,
)
from the_watcher.worker_client import call_worker

router = APIRouter(tags=["stand_in"])


@router.post("/api/v1/watcher/stand-in/act", response_model=StandInAction)
async def stand_in_act(req: StandInRequest) -> StandInAction:
    """Simulate an action for an absent player's character with applied penalties.

    With a worker configured, a worker failure is returned as HTTP 503. The Watcher never
    substitutes canned output for a failed worker call.
    """
    stand_in: StandInAction
    guardrails = req.guardrails.model_dump() if req.guardrails is not None else None
    if INFERENCE_URL:
        data = await call_worker(
            INFERENCE_URL,
            "/inference/v1/stand-in-action",
            {
                "campaign_id": req.campaign_id,
                "session_id": req.session_id,
                "character_name": req.character_name,
                "character_class": req.character_class,
                "penalties": req.penalties,
                "scene_context": req.scene_context,
                "personality_traits": req.personality_traits,
                "guardrails": guardrails,
            },
            timeout=10.0,
        )
        stand_in = StandInAction(
            character_name=data["character_name"],
            action_type=data["action_type"],
            action_description=data["narrative_flavor"],
            dialogue=data["dialogue"],
            penalties_applied=data["penalties_applied"],
            guardrails_applied=data["guardrails_applied"],
            flavor_text=data["narrative_flavor"],
            source=data["source"],
            degraded=data["degraded"],
        )
    else:
        stand_in = engine.generate_stand_in_action(
            character_name=req.character_name,
            character_class=req.character_class,
            penalties=req.penalties,
            scene_context=req.scene_context,
            personality_traits=req.personality_traits,
            guardrails=guardrails,
        )

    # Publish events to Redis Streams
    bus = get_event_bus()
    session_uuid = to_uuid(req.session_id)
    campaign_uuid = to_uuid(req.campaign_id)

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
async def stand_in_recap(req: StandInRecapRequest) -> StandInRecapResponse:
    """Generate a humorous recap of an absent player's stand-in exploits for when they return."""
    data = engine.generate_stand_in_recap(
        character_name=req.character_name,
        actions=req.actions,
        penalties=req.penalties,
    )
    return StandInRecapResponse.model_validate(data)
