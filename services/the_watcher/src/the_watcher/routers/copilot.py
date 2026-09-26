"""DM Co-Pilot router: whispers, pre-execution pause window, and veto override endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query
from runefoble_events.events import (
    DMNarrativeWhispered,
    WatcherActionApproved,
    WatcherActionModified,
    WatcherActionProposed,
    WatcherActionVetoed,
)
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
    ApproveActionRequest,
    ModifyActionRequest,
    PendingAction,
    ProposeActionRequest,
    VetoActionRequest,
    WhisperCreateRequest,
    WhisperGenerateRequest,
    WhisperListResponse,
    WhisperSuggestion,
)

router = APIRouter(tags=["copilot"])


def _extract_caller_id(x_user_id: str | None, user_id: str | None) -> str | None:
    return x_user_id or user_id


# -----------------------------------------------------------------------------
# Action Interceptor (Propose, Veto, Approve, Modify)
# -----------------------------------------------------------------------------


@router.post("/api/v1/watcher/actions/propose", response_model=PendingAction)
@router.post("/api/v1/watcher/propose", response_model=PendingAction)
async def propose_action(req: ProposeActionRequest) -> PendingAction:
    """Propose an AI game mutation with a pre-execution pause window (default 2000ms)."""
    engine = get_copilot_engine()
    action = engine.propose_action(req)

    bus = get_event_bus()
    event = WatcherActionProposed(
        aggregate_id=to_uuid(req.session_id),
        action_id=action.action_id,
        session_id=str(req.session_id),
        campaign_id=str(req.campaign_id) if req.campaign_id else "",
        actor_name=req.actor_name,
        action_type=req.action_type,
        description=req.description,
        target=req.target,
        parameters=req.parameters,
        pause_window_ms=action.pause_window_ms,
    )
    try:
        await bus.publish_event(STREAM_WATCHER, event)
    except Exception as e:
        logger.warning("Failed to publish WatcherActionProposed event: %s", e)

    return action


@router.post("/api/v1/watcher/veto")
async def veto_action(
    req: VetoActionRequest,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    user_id: Annotated[str | None, Query(alias="user_id")] = None,
):
    """Cancel pending action execution and emit WatcherActionVetoed. Requires DM permission."""
    caller = _extract_caller_id(x_user_id, user_id)
    engine = get_copilot_engine()
    pending = engine.get_pending_action(req.action_id)

    target_campaign = req.campaign_id or (pending.campaign_id if pending else None)
    target_session = req.session_id or (pending.session_id if pending else None)

    is_dm = await check_dm_authorization(
        caller,
        campaign_id=target_campaign,
        session_id=target_session,
        spicedb=get_spicedb_client(),
    )
    if not is_dm:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Zanzibar authorization denied. User lacks dungeon_master permission.",
        )

    action = engine.veto_action(req.action_id, vetoed_by=caller or "unknown", reason=req.reason)

    bus = get_event_bus()
    event = WatcherActionVetoed(
        aggregate_id=to_uuid(action.session_id),
        action_id=action.action_id,
        session_id=str(action.session_id),
        campaign_id=str(action.campaign_id) if action.campaign_id else "",
        vetoed_by=caller or "unknown",
        reason=req.reason,
        original_action=action.model_dump(),
    )
    try:
        await bus.publish_event(STREAM_WATCHER, event)
    except Exception as e:
        logger.warning("Failed to publish WatcherActionVetoed event: %s", e)

    return {
        "status": "vetoed",
        "action_id": action.action_id,
        "vetoed_by": caller,
        "reason": req.reason,
    }


@router.post("/api/v1/watcher/approve")
async def approve_action(
    req: ApproveActionRequest,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    user_id: Annotated[str | None, Query(alias="user_id")] = None,
):
    """Commit pending action immediately. Requires DM permission."""
    caller = _extract_caller_id(x_user_id, user_id)
    engine = get_copilot_engine()
    pending = engine.get_pending_action(req.action_id)

    target_campaign = req.campaign_id or (pending.campaign_id if pending else None)
    target_session = req.session_id or (pending.session_id if pending else None)

    is_dm = await check_dm_authorization(
        caller,
        campaign_id=target_campaign,
        session_id=target_session,
        spicedb=get_spicedb_client(),
    )
    if not is_dm:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Zanzibar authorization denied. User lacks dungeon_master permission.",
        )

    action = await engine.approve_action(req.action_id, approved_by=caller or "unknown")

    bus = get_event_bus()
    event = WatcherActionApproved(
        aggregate_id=to_uuid(action.session_id),
        action_id=action.action_id,
        session_id=str(action.session_id),
        campaign_id=str(action.campaign_id) if action.campaign_id else "",
        approved_by=caller or "unknown",
        action_type=action.action_type,
        parameters=action.parameters,
    )
    try:
        await bus.publish_event(STREAM_WATCHER, event)
    except Exception as e:
        logger.warning("Failed to publish WatcherActionApproved event: %s", e)

    return {
        "status": "approved",
        "action_id": action.action_id,
        "approved_by": caller,
    }


@router.post("/api/v1/watcher/modify")
async def modify_action(
    req: ModifyActionRequest,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    user_id: Annotated[str | None, Query(alias="user_id")] = None,
):
    """Modify parameters or intent of a pending action before execution. Requires DM permission."""
    caller = _extract_caller_id(x_user_id, user_id)
    engine = get_copilot_engine()
    pending = engine.get_pending_action(req.action_id)

    target_campaign = req.campaign_id or (pending.campaign_id if pending else None)
    target_session = req.session_id or (pending.session_id if pending else None)

    is_dm = await check_dm_authorization(
        caller,
        campaign_id=target_campaign,
        session_id=target_session,
        spicedb=get_spicedb_client(),
    )
    if not is_dm:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Zanzibar authorization denied. User lacks dungeon_master permission.",
        )

    action = await engine.modify_action(
        req.action_id,
        modified_by=caller or "unknown",
        description=req.description,
        target=req.target,
        parameters=req.parameters,
        auto_approve=req.auto_approve,
    )

    bus = get_event_bus()
    event = WatcherActionModified(
        aggregate_id=to_uuid(action.session_id),
        action_id=action.action_id,
        session_id=str(action.session_id),
        campaign_id=str(action.campaign_id) if action.campaign_id else "",
        modified_by=caller or "unknown",
        description=action.description,
        target=action.target,
        parameters=action.parameters,
    )
    try:
        await bus.publish_event(STREAM_WATCHER, event)
    except Exception as e:
        logger.warning("Failed to publish WatcherActionModified event: %s", e)

    return {
        "status": action.status,
        "action_id": action.action_id,
        "modified_by": caller,
        "target": action.target,
        "description": action.description,
        "parameters": action.parameters,
    }


@router.get("/api/v1/watcher/actions/pending", response_model=list[PendingAction])
async def list_pending_actions(
    session_id: str | None = None,
    campaign_id: str | None = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    user_id: Annotated[str | None, Query(alias="user_id")] = None,
) -> list[PendingAction]:
    """Retrieve all pending actions. Requires DM permission."""
    caller = _extract_caller_id(x_user_id, user_id)
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

    engine = get_copilot_engine()
    return engine.list_pending_actions(session_id=session_id, campaign_id=campaign_id)


# -----------------------------------------------------------------------------
# Private DM Whispers Channel
# -----------------------------------------------------------------------------


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
    is_dm = await check_dm_authorization(
        caller,
        campaign_id=req.campaign_id,
        session_id=req.session_id,
        spicedb=get_spicedb_client(),
    )
    if not is_dm:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Zanzibar authorization denied. User lacks dungeon_master permission.",
        )

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
    is_dm = await check_dm_authorization(
        caller,
        campaign_id=req.campaign_id,
        session_id=req.session_id,
        spicedb=get_spicedb_client(),
    )
    if not is_dm:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Zanzibar authorization denied. User lacks dungeon_master permission.",
        )

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
