"""Action interceptor sub-router: propose, pause window countdown, approve, modify, and veto."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from runefoble_events.events import (
    WatcherActionApproved,
    WatcherActionModified,
    WatcherActionProposed,
    WatcherActionVetoed,
)
from runefoble_platform.event_publish import publish_best_effort, publish_or_fail
from the_watcher.dependencies import (
    STREAM_WATCHER,
    get_copilot_engine,
    get_event_bus,
    require_dm,
    require_session_permission,
    to_uuid,
)
from the_watcher.identity import CallerId, get_caller_principal
from the_watcher.models import (
    ApproveActionRequest,
    ModifyActionRequest,
    PendingAction,
    ProposeActionRequest,
    VetoActionRequest,
)

router = APIRouter(dependencies=[Depends(get_caller_principal)], tags=["copilot"])


def _planned_action(
    action_id: str, session_id: str | None, campaign_id: str | None
) -> PendingAction:
    """Return a copy of the pending action that the engine is about to change.

    Decision routes publish the audit event from this copy before the engine mutates state.
    A failed publish then leaves the real pending action unchanged.
    """
    existing = get_copilot_engine().get_pending_action(action_id)
    if existing is not None:
        return existing.model_copy(deep=True)
    return PendingAction(
        action_id=action_id,
        session_id=session_id or "unknown",
        campaign_id=campaign_id or "",
        actor_name="unknown",
        action_type="unknown",
        description="Unknown action",
    )


@router.post("/api/v1/watcher/actions/propose", response_model=PendingAction)
@router.post("/api/v1/watcher/propose", response_model=PendingAction)
async def propose_action(caller_id: CallerId, req: ProposeActionRequest) -> PendingAction:
    """Propose an AI game mutation with a pre-execution pause window (default 2000ms)."""
    await require_session_permission(caller_id, req.session_id, "session.participate")
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
    await publish_best_effort(bus, STREAM_WATCHER, event)

    return action


@router.post("/api/v1/watcher/veto")
async def veto_action(
    caller_id: CallerId,
    req: VetoActionRequest,
):
    """Cancel pending action execution and emit WatcherActionVetoed. Requires DM permission."""
    caller = caller_id
    engine = get_copilot_engine()
    pending = engine.get_pending_action(req.action_id)

    target_campaign = req.campaign_id or (pending.campaign_id if pending else None)
    target_session = req.session_id or (pending.session_id if pending else None)
    await require_dm(caller, target_campaign, target_session)

    planned = _planned_action(req.action_id, target_session, target_campaign)
    planned.status = "vetoed"
    planned.vetoed_by = caller or "unknown"
    planned.veto_reason = req.reason
    event = WatcherActionVetoed(
        aggregate_id=to_uuid(planned.session_id),
        action_id=planned.action_id,
        session_id=str(planned.session_id),
        campaign_id=str(planned.campaign_id) if planned.campaign_id else "",
        vetoed_by=caller or "unknown",
        reason=req.reason,
        original_action=planned.model_dump(),
    )
    await publish_or_fail(get_event_bus(), STREAM_WATCHER, event)

    action = engine.veto_action(req.action_id, vetoed_by=caller or "unknown", reason=req.reason)

    return {
        "status": "vetoed",
        "action_id": action.action_id,
        "vetoed_by": caller,
        "reason": req.reason,
    }


@router.post("/api/v1/watcher/approve")
async def approve_action(
    caller_id: CallerId,
    req: ApproveActionRequest,
):
    """Commit pending action immediately. Requires DM permission."""
    caller = caller_id
    engine = get_copilot_engine()
    pending = engine.get_pending_action(req.action_id)

    target_campaign = req.campaign_id or (pending.campaign_id if pending else None)
    target_session = req.session_id or (pending.session_id if pending else None)
    await require_dm(caller, target_campaign, target_session)

    planned = _planned_action(req.action_id, target_session, target_campaign)
    planned.status = "approved"
    planned.approved_by = caller or "unknown"
    event = WatcherActionApproved(
        aggregate_id=to_uuid(planned.session_id),
        action_id=planned.action_id,
        session_id=str(planned.session_id),
        campaign_id=str(planned.campaign_id) if planned.campaign_id else "",
        approved_by=caller or "unknown",
        action_type=planned.action_type,
        parameters=planned.parameters,
    )
    await publish_or_fail(get_event_bus(), STREAM_WATCHER, event)

    action = await engine.approve_action(req.action_id, approved_by=caller or "unknown")

    return {
        "status": "approved",
        "action_id": action.action_id,
        "approved_by": caller,
    }


@router.post("/api/v1/watcher/modify")
async def modify_action(
    caller_id: CallerId,
    req: ModifyActionRequest,
):
    """Modify parameters or intent of a pending action before execution. Requires DM permission."""
    caller = caller_id
    engine = get_copilot_engine()
    pending = engine.get_pending_action(req.action_id)

    target_campaign = req.campaign_id or (pending.campaign_id if pending else None)
    target_session = req.session_id or (pending.session_id if pending else None)
    await require_dm(caller, target_campaign, target_session)

    planned = _planned_action(req.action_id, target_session, target_campaign)
    if req.description is not None:
        planned.description = req.description
    if req.target is not None:
        planned.target = req.target
    if req.parameters is not None:
        planned.parameters.update(req.parameters)
    planned.modified_by = caller or "unknown"
    event = WatcherActionModified(
        aggregate_id=to_uuid(planned.session_id),
        action_id=planned.action_id,
        session_id=str(planned.session_id),
        campaign_id=str(planned.campaign_id) if planned.campaign_id else "",
        modified_by=caller or "unknown",
        description=planned.description,
        target=planned.target,
        parameters=planned.parameters,
    )
    await publish_or_fail(get_event_bus(), STREAM_WATCHER, event)

    action = await engine.modify_action(
        req.action_id,
        modified_by=caller or "unknown",
        description=req.description,
        target=req.target,
        parameters=req.parameters,
        auto_approve=req.auto_approve,
    )

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
    caller_id: CallerId,
    session_id: str | None = None,
    campaign_id: str | None = None,
) -> list[PendingAction]:
    """Retrieve all pending actions. Requires DM permission."""
    caller = caller_id
    await require_dm(caller, campaign_id, session_id)

    engine = get_copilot_engine()
    return engine.list_pending_actions(session_id=session_id, campaign_id=campaign_id)
