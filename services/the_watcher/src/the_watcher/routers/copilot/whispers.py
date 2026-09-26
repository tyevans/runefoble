"""DM private whispers sub-router: list, create, and generate narrative suggestions."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query
from runefoble_events.events import DMNarrativeWhispered
from the_watcher.dependencies import (
    STREAM_WATCHER,
    check_dm_authorization,
    get_copilot_engine,
    get_event_bus,
    get_spicedb_client,
    logger,
    to_uuid,
)
from the_watcher.models import (
    WhisperCreateRequest,
    WhisperGenerateRequest,
    WhisperListResponse,
    WhisperSuggestion,
)

router = APIRouter(tags=["copilot"])


def _extract_caller_id(x_user_id: str | None, user_id: str | None) -> str | None:
    return x_user_id or user_id


async def _assert_dm_permission(
    caller: str | None, campaign_id: str | None, session_id: str | None
) -> None:
    is_dm = await check_dm_authorization(
        caller,
        campaign_id=campaign_id,
        session_id=session_id,
        spicedb=get_spicedb_client(),
    )
    if not is_dm:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Zanzibar authorization denied. User lacks dungeon_master permission.",
        )


@router.get("/api/v1/watcher/whispers", response_model=WhisperListResponse)
async def get_whispers(
    session_id: str,
    campaign_id: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    whisper_type: str | None = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    user_id: Annotated[str | None, Query(alias="user_id")] = None,
) -> WhisperListResponse:
    """Return paginated DM private narrative suggestions. Restricted to dungeon_master relation."""
    caller = _extract_caller_id(x_user_id, user_id)
    await _assert_dm_permission(caller, campaign_id, session_id)

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
    req: WhisperCreateRequest,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    user_id: Annotated[str | None, Query(alias="user_id")] = None,
) -> WhisperSuggestion:
    """Add a private narrative suggestion to the DM channel. Restricted to dungeon_master."""
    caller = _extract_caller_id(x_user_id, user_id)
    await _assert_dm_permission(caller, req.campaign_id, req.session_id)

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
    try:
        await bus.publish_event(STREAM_WATCHER, event)
    except Exception as e:
        logger.warning("Failed to publish DMNarrativeWhispered event: %s", e)

    return created


@router.post("/api/v1/watcher/whispers/generate", response_model=list[WhisperSuggestion])
async def generate_whispers(
    req: WhisperGenerateRequest,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    user_id: Annotated[str | None, Query(alias="user_id")] = None,
) -> list[WhisperSuggestion]:
    """Generate dynamic narrative suggestions, monster tactics, and passive perception cues."""
    caller = _extract_caller_id(x_user_id, user_id)
    await _assert_dm_permission(caller, req.campaign_id, req.session_id)

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
        try:
            await bus.publish_event(STREAM_WATCHER, event)
        except Exception as e:
            logger.warning("Failed to publish DMNarrativeWhispered event: %s", e)

    return whispers
