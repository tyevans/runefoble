"""AI Stand-in action simulation and recap routes for The Watcher service."""

from __future__ import annotations

import httpx
from fastapi import APIRouter
from runefoble_events.events import AbsencePenaltyApplied, StandInActionDecided
from the_watcher.dependencies import (
    INFERENCE_URL,
    STREAM_WATCHER,
    engine,
    get_event_bus,
    logger,
    to_uuid,
)
from the_watcher.models import (
    StandInAction,
    StandInRecapRequest,
    StandInRecapResponse,
    StandInRequest,
)

router = APIRouter(tags=["stand_in"])


@router.post("/api/v1/watcher/stand-in/act", response_model=StandInAction)
async def stand_in_act(req: StandInRequest) -> StandInAction:
    """Simulate an action for an absent player's character with applied penalties."""
    stand_in: StandInAction | None = None
    if INFERENCE_URL:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{INFERENCE_URL}/inference/v1/stand-in-action",
                    json={
                        "campaign_id": req.campaign_id or "current-campaign",
                        "session_id": req.session_id or "current-session",
                        "character_name": req.character_name,
                        "character_class": req.character_class,
                        "penalties": req.penalties,
                        "scene_context": req.scene_context,
                        "personality_traits": req.personality_traits,
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    stand_in = StandInAction(
                        character_name=data.get("character_name", req.character_name),
                        action_type=data.get("action_type", "attack"),
                        action_description=data.get("narrative_flavor", ""),
                        dialogue=data.get("dialogue", "..."),
                        penalties_applied=data.get("penalties_applied", req.penalties),
                        flavor_text=data.get("narrative_flavor", ""),
                    )
        except Exception as e:
            logger.warning("Inference worker failed: %s. Falling back to local engine.", e)

    if stand_in is None:
        stand_in = engine.generate_stand_in_action(
            character_name=req.character_name,
            character_class=req.character_class,
            penalties=req.penalties,
            scene_context=req.scene_context,
            personality_traits=req.personality_traits,
        )

    # Publish events to Redis Streams
    bus = get_event_bus()
    session_uuid = to_uuid(req.session_id)
    campaign_uuid = to_uuid(req.campaign_id) if req.campaign_id else None

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

    try:
        await bus.publish_event(STREAM_WATCHER, action_event)
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
                await bus.publish_event(STREAM_WATCHER, pen_event)
    except Exception as e:
        logger.warning(
            "Failed to publish stand-in events to Redis stream '%s': %s", STREAM_WATCHER, e
        )

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
