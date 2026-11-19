"""Action interceptor sub-router: propose, pause window countdown, approve, modify, and veto."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from the_watcher.dependencies import (
    get_copilot_engine,
    require_dm,
    require_session_permission,
)
from the_watcher.identity import CallerId, get_principal
from the_watcher.models import (
    ApproveActionRequest,
    ModifyActionRequest,
    PendingAction,
    ProposeActionRequest,
    VetoActionRequest,
)

router = APIRouter(dependencies=[Depends(get_principal)], tags=["copilot"])


@router.post("/api/v1/watcher/actions/propose", response_model=PendingAction)
async def propose_action(caller_id: CallerId, req: ProposeActionRequest) -> PendingAction:
    """Propose an AI game mutation with a pre-execution pause window (default 2000ms)."""
    await require_session_permission(caller_id, req.session_id, "session.participate")
    return await get_copilot_engine().propose_action(req)


@router.post("/api/v1/watcher/veto")
async def veto_action(caller_id: CallerId, req: VetoActionRequest):
    """Cancel pending action execution. Requires DM permission."""
    await require_dm(caller_id, req.campaign_id, req.session_id)
    action = await get_copilot_engine().veto_action(
        req.session_id, req.action_id, vetoed_by=caller_id or "unknown", reason=req.reason
    )
    return {
        "status": "vetoed",
        "action_id": action.action_id,
        "vetoed_by": caller_id,
        "reason": req.reason,
    }


@router.post("/api/v1/watcher/approve")
async def approve_action(caller_id: CallerId, req: ApproveActionRequest):
    """Commit pending action immediately. Requires DM permission."""
    await require_dm(caller_id, req.campaign_id, req.session_id)
    action = await get_copilot_engine().approve_action(
        req.session_id, req.action_id, approved_by=caller_id or "unknown"
    )
    return {
        "status": "approved",
        "action_id": action.action_id,
        "approved_by": caller_id,
        "execution_error": action.execution_error,
    }


@router.post("/api/v1/watcher/modify")
async def modify_action(caller_id: CallerId, req: ModifyActionRequest):
    """Modify parameters or intent of a pending action before execution. Requires DM permission."""
    await require_dm(caller_id, req.campaign_id, req.session_id)
    action = await get_copilot_engine().modify_action(
        req.session_id,
        req.action_id,
        modified_by=caller_id or "unknown",
        description=req.description,
        target=req.target,
        parameters=req.parameters,
        auto_approve=req.auto_approve,
    )
    return {
        "status": action.status,
        "action_id": action.action_id,
        "modified_by": caller_id,
        "target": action.target,
        "description": action.description,
        "parameters": action.parameters,
        "execution_error": action.execution_error,
    }


@router.get("/api/v1/watcher/actions/pending", response_model=list[PendingAction])
async def list_pending_actions(
    caller_id: CallerId,
    session_id: str,
    campaign_id: str | None = None,
) -> list[PendingAction]:
    """Retrieve every action the session holds with its status. Requires DM permission."""
    await require_dm(caller_id, campaign_id, session_id)
    return await get_copilot_engine().list_pending_actions(session_id, campaign_id)
