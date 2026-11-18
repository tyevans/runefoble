"""DM private whispers sub-router: list, create, and generate narrative suggestions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from runefoble_events.events import DMNarrativeWhispered
from runefoble_platform.event_publish import publish_best_effort, publish_or_fail
from the_watcher.dependencies import (
    STREAM_WATCHER,
    get_copilot_engine,
    get_event_bus,
    require_dm,
    to_uuid,
)
from the_watcher.identity import CallerId, get_caller_principal
from the_watcher.models import (
    WhisperCreateRequest,
    WhisperGenerateRequest,
    WhisperListResponse,
    WhisperSuggestion,
)

router = APIRouter(dependencies=[Depends(get_caller_principal)], tags=["copilot"])


@router.get("/api/v1/watcher/whispers", response_model=WhisperListResponse)
async def get_whispers(
    caller_id: CallerId,
    session_id: str,
    campaign_id: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    whisper_type: str | None = None,
) -> WhisperListResponse:
    """Return paginated DM private narrative suggestions. Restricted to dungeon_master relation."""
    caller = caller_id
    await require_dm(caller, campaign_id, session_id)

    engine = get_copilot_engine()
    items, total = engine.list_whispers(
        session_id=session_id,
        campaign_id=campaign_id,
        page=page,
        limit=limit,
        whisper_type=whisper_type,
    )
    return WhisperListResponse(whispers=items, total=total, page=page, limit=limit)


@router.post("/api/v1/watcher/whispers", response_model=WhisperSuggestion)
async def create_whisper(
    caller_id: CallerId,
    req: WhisperCreateRequest,
) -> WhisperSuggestion:
    """Add a private narrative suggestion to the DM channel. Restricted to dungeon_master."""
    caller = caller_id
    await require_dm(caller, req.campaign_id, req.session_id)

    engine = get_copilot_engine()
    whisper = WhisperSuggestion(
        whisper_id="",
        session_id=req.session_id,
        campaign_id=req.campaign_id,
        whisper_type=req.whisper_type,
        content=req.content,
        metadata=req.metadata,
    )
    created = engine.add_whisper(whisper)

    bus = get_event_bus()
    event = DMNarrativeWhispered(
        aggregate_id=to_uuid(created.session_id),
        whisper_id=created.whisper_id,
        session_id=str(created.session_id),
        campaign_id=str(created.campaign_id) if created.campaign_id else "",
        whisper_type=created.whisper_type,
        content=created.content,
        recipient_role=created.recipient_role,
        metadata=created.metadata,
    )
    await publish_or_fail(bus, STREAM_WATCHER, event)

    return created


@router.post("/api/v1/watcher/whispers/generate", response_model=list[WhisperSuggestion])
async def generate_whispers(
    caller_id: CallerId,
    req: WhisperGenerateRequest,
) -> list[WhisperSuggestion]:
    """Generate dynamic narrative suggestions, monster tactics, and passive perception cues."""
    caller = caller_id
    await require_dm(caller, req.campaign_id, req.session_id)

    engine = get_copilot_engine()
    whispers = engine.generate_default_whispers(
        session_id=req.session_id,
        campaign_id=req.campaign_id,
        scene_context=req.scene_context,
        location_type=req.location_type,
        threat_level=req.threat_level,
    )

    bus = get_event_bus()
    for w in whispers:
        event = DMNarrativeWhispered(
            aggregate_id=to_uuid(w.session_id),
            whisper_id=w.whisper_id,
            session_id=str(w.session_id),
            campaign_id=str(w.campaign_id) if w.campaign_id else "",
            whisper_type=w.whisper_type,
            content=w.content,
            recipient_role=w.recipient_role,
            metadata=w.metadata,
        )
        await publish_best_effort(bus, STREAM_WATCHER, event)

    return whispers
