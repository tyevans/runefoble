"""Absentee chronicle and session recap routes for The Watcher service."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from runefoble_events.events import AbsenteeRecapGenerated
from runefoble_platform.event_publish import publish_best_effort
from the_watcher.container_access import Engines, EventBus
from the_watcher.dependencies import STREAM_WATCHER, require_session_permission
from the_watcher.identity import CallerId, get_principal
from the_watcher.models import RecapRequest

router = APIRouter(dependencies=[Depends(get_principal)], tags=["chronicle"])


@router.post("/api/v1/watcher/chronicle/recap", response_model=AbsenteeRecapGenerated)
async def generate_chronicle_recap(
    engines: Engines, event_bus: EventBus, caller_id: CallerId, req: RecapRequest
) -> AbsenteeRecapGenerated:
    """Generate a humorous absentee session chronicle and recap event for a returning player."""
    await require_session_permission(caller_id, req.session_id, "session.observe")
    recap_event = engines.chronicle.generate_recap(
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
    await publish_best_effort(event_bus.get(), STREAM_WATCHER, recap_event)
    return recap_event
