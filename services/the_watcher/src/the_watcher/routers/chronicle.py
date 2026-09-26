"""Absentee chronicle and session recap routes for The Watcher service."""

from __future__ import annotations

from fastapi import APIRouter
from runefoble_events.events import AbsenteeRecapGenerated
from the_watcher.dependencies import (
    STREAM_WATCHER,
    chronicle_engine,
    get_event_bus,
    logger,
)
from the_watcher.models import RecapRequest

router = APIRouter(tags=["chronicle"])


@router.post("/api/v1/watcher/chronicle/recap", response_model=AbsenteeRecapGenerated)
async def generate_chronicle_recap(req: RecapRequest) -> AbsenteeRecapGenerated:
    """Generate a humorous absentee session chronicle and recap event for a returning player."""
    recap_event = chronicle_engine.generate_recap(
        session_id=req.session_id,
        character_id=req.character_id,
        character_name=req.character_name,
        stand_in_persona=req.stand_in_persona,
        penalties=req.penalties,
        actions=req.actions,
        hp_delta=req.hp_delta,
        items_acquired=req.items_acquired,
        audio_url=req.audio_url,
    )
    bus = get_event_bus()
    try:
        await bus.publish_event(STREAM_WATCHER, recap_event)
    except Exception as e:
        logger.warning(
            "Failed to publish AbsenteeRecapGenerated event to Redis stream '%s': %s",
            STREAM_WATCHER,
            e,
        )
    return recap_event
