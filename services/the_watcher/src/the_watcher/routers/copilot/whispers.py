"""DM private whispers sub-router: list, create, and generate narrative suggestions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from the_watcher.dependencies import get_whisper_service, require_dm
from the_watcher.identity import CallerId, get_principal
from the_watcher.models import (
    WhisperCreateRequest,
    WhisperGenerateRequest,
    WhisperListResponse,
    WhisperSuggestion,
)

router = APIRouter(dependencies=[Depends(get_principal)], tags=["copilot"])


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
    await require_dm(caller_id, campaign_id, session_id)

    items, total = await get_whisper_service().list_whispers(
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
    await require_dm(caller_id, req.campaign_id, req.session_id)

    whisper = WhisperSuggestion(
        whisper_id="",
        session_id=req.session_id,
        campaign_id=req.campaign_id,
        whisper_type=req.whisper_type,
        content=req.content,
        metadata=req.metadata,
    )
    return await get_whisper_service().add_whisper(whisper)


@router.post("/api/v1/watcher/whispers/generate", response_model=list[WhisperSuggestion])
async def generate_whispers(
    caller_id: CallerId,
    req: WhisperGenerateRequest,
) -> list[WhisperSuggestion]:
    """Generate dynamic narrative suggestions, monster tactics, and passive perception cues."""
    await require_dm(caller_id, req.campaign_id, req.session_id)

    return await get_whisper_service().generate_whispers(
        session_id=req.session_id,
        campaign_id=req.campaign_id,
        scene_context=req.scene_context,
        location_type=req.location_type,
        threat_level=req.threat_level,
    )
