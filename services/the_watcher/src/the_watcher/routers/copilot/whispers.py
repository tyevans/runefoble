"""DM private whispers sub-router: list, create, and generate narrative suggestions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from the_watcher.container_access import Engines, EventBus, Repos, Whispers
from the_watcher.dependencies import require_dm
from the_watcher.engine_selection import load_watcher_ports
from the_watcher.identity import CallerId, get_principal
from the_watcher.models import (
    WhisperCreateRequest,
    WhisperDispatchRequest,
    WhisperGenerateRequest,
    WhisperListResponse,
    WhisperSuggestion,
)
from the_watcher.narrative_dispatch import dispatch_audience_narration

router = APIRouter(dependencies=[Depends(get_principal)], tags=["copilot"])


@router.get("/api/v1/watcher/whispers", response_model=WhisperListResponse)
async def get_whispers(
    whispers: Whispers,
    engines: Engines,
    caller_id: CallerId,
    session_id: str,
    campaign_id: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    whisper_type: str | None = None,
) -> WhisperListResponse:
    """Return paginated DM private narrative suggestions. Restricted to dungeon_master relation.

    The reply names the engine of the narration port, so the DM sees when no model is set.
    """
    await require_dm(caller_id, campaign_id, session_id)

    items, total = await whispers.list_whispers(
        session_id=session_id,
        campaign_id=campaign_id,
        page=page,
        limit=limit,
        whisper_type=whisper_type,
    )
    narration_engine = load_watcher_ports(engines.watcher).narrator.engine_name
    return WhisperListResponse(
        whispers=items, total=total, page=page, limit=limit, narration_engine=narration_engine
    )


@router.post("/api/v1/watcher/whispers", response_model=WhisperSuggestion)
async def create_whisper(
    whispers: Whispers,
    caller_id: CallerId,
    req: WhisperCreateRequest,
) -> WhisperSuggestion:
    """Add a private narrative suggestion to the DM channel. Restricted to dungeon_master."""
    await require_dm(caller_id, req.campaign_id, req.session_id)

    whisper = WhisperSuggestion(
        whisper_id="",
        session_id=req.session_id,
        campaign_id=req.campaign_id,
        whisper_type=req.whisper_type,
        content=req.content,
        metadata=req.metadata,
    )
    return await whispers.add_whisper(whisper)


@router.post("/api/v1/watcher/whispers/generate", response_model=list[WhisperSuggestion])
async def generate_whispers(
    whispers: Whispers,
    engines: Engines,
    caller_id: CallerId,
    req: WhisperGenerateRequest,
) -> list[WhisperSuggestion]:
    """Ask the narration port for a DM whisper and record it. Restricted to dungeon_master.

    The text comes only from the language model. A port without an engine, or a failed engine,
    answers 503 and records no whisper (TASK-0949).
    """
    await require_dm(caller_id, req.campaign_id, req.session_id)
    narrator = load_watcher_ports(engines.watcher).narrator
    return await whispers.generate_whispers(narrator, req)


@router.post(
    "/api/v1/watcher/whispers/{whisper_id}/dispatch",
    response_model=WhisperSuggestion,
)
async def dispatch_whisper(
    repos: Repos,
    event_bus: EventBus,
    caller_id: CallerId,
    whisper_id: str,
    req: WhisperDispatchRequest,
) -> WhisperSuggestion:
    """Send an audience narration to the table. Restricted to the session controller (DM).

    The DM may send edited text. A second dispatch of the same whisper answers 409.
    """
    await require_dm(caller_id, req.campaign_id or None, req.session_id)
    return await dispatch_audience_narration(
        bus=event_bus.get(),
        whisper_repo=repos.whispers,
        session_id=req.session_id,
        campaign_id=req.campaign_id,
        whisper_id=whisper_id,
        text=req.text,
    )
