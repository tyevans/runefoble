"""Absentee chronicle and session recap routes for The Watcher service."""

from __future__ import annotations

from fastapi import APIRouter
from runefoble_events.events import AbsenteeRecapGenerated
from runefoble_platform.event_publish import publish_best_effort
from the_watcher.dependencies import (
    STREAM_WATCHER,
    chronicle_engine,
    get_event_bus,
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
    await publish_best_effort(bus, STREAM_WATCHER, recap_event)
    return recap_event
