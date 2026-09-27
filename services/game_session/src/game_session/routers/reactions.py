"""API endpoints for spoken reaction interrupts and ready-action conditional triggers."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from game_session.dependencies import repo
from game_session.models import (
    DeclareReactionRequest,
    DeclareReactionResponse,
    EvaluateTriggersRequest,
    EvaluateTriggersResponse,
    ReadyActionRequest,
    ReadyActionResponse,
    ResolveReactionRequest,
    ResolveReactionResponse,
)
from game_session.reactions.interrupt_coordinator import ReactionInterruptCoordinator
from game_session.reactions.ready_action_registry import ReadyActionRegistry

router = APIRouter(tags=["reactions"])

_coordinator = ReactionInterruptCoordinator(repo)
_registry = ReadyActionRegistry(repo)


def init_reaction_dependencies(
    coordinator: ReactionInterruptCoordinator | None = None,
    registry: ReadyActionRegistry | None = None,
) -> None:
    """Dependency injection hook for testing reaction coordinators."""
    global _coordinator, _registry
    if coordinator is not None:
        _coordinator = coordinator
    if registry is not None:
        _registry = registry


@router.post("/sessions/{session_id}/reactions/declare", response_model=DeclareReactionResponse)
@router.post(
    "/api/v1/sessions/{session_id}/reactions/declare", response_model=DeclareReactionResponse
)
async def declare_reaction_interrupt(
    session_id: UUID, req: DeclareReactionRequest
) -> DeclareReactionResponse:
    """Halt active combat turn and initiate a spoken reaction window."""
    try:
        return await _coordinator.declare_reaction(
            session_id=session_id,
            reacting_combatant_id=req.reacting_combatant_id,
            trigger_phrase=req.trigger_phrase,
            reaction_type=req.reaction_type,
            reacting_combatant_name=req.reacting_combatant_name,
            timeout_seconds=req.timeout_seconds,
            target_id=req.target_id,
            details=req.details,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}") from e


@router.post("/sessions/{session_id}/reactions/ready-action", response_model=ReadyActionResponse)
@router.post(
    "/api/v1/sessions/{session_id}/reactions/ready-action", response_model=ReadyActionResponse
)
async def register_ready_action_trigger(
    session_id: UUID, req: ReadyActionRequest
) -> ReadyActionResponse:
    """Register a conditional ready-action trigger evaluated against combat events."""
    try:
        return await _registry.register_ready_action(
            session_id=session_id,
            combatant_id=req.combatant_id,
            combatant_name=req.combatant_name,
            trigger_type=req.trigger_type,
            trigger_condition=req.trigger_condition,
            readied_action=req.readied_action,
            target_id=req.target_id,
            range_cells=req.range_cells,
            details=req.details,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}") from e


@router.post(
    "/sessions/{session_id}/reactions/{reaction_id}/resolve",
    response_model=ResolveReactionResponse,
)
@router.post(
    "/api/v1/sessions/{session_id}/reactions/{reaction_id}/resolve",
    response_model=ResolveReactionResponse,
)
async def resolve_reaction_interrupt(
    session_id: UUID, reaction_id: str, req: ResolveReactionRequest | None = None
) -> ResolveReactionResponse:
    """Resolve or dismiss declared reaction interrupt, resuming the combat turn."""
    action_taken = req.action_taken if req else "executed"
    details = req.details if req else {}
    try:
        return await _coordinator.resolve_reaction(
            session_id=session_id,
            reaction_id=reaction_id,
            action_taken=action_taken,
            details=details,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}") from e


@router.post(
    "/sessions/{session_id}/reactions/evaluate-triggers",
    response_model=EvaluateTriggersResponse,
)
@router.post(
    "/api/v1/sessions/{session_id}/reactions/evaluate-triggers",
    response_model=EvaluateTriggersResponse,
)
async def evaluate_ready_action_triggers(
    session_id: UUID, req: EvaluateTriggersRequest
) -> EvaluateTriggersResponse:
    """Evaluate domain events against ready-action triggers for this session."""
    try:
        triggered = await _registry.evaluate_triggers(
            session_id=session_id,
            event_type=req.event_type,
            event_data=req.event_data,
        )
        return EvaluateTriggersResponse(
            session_id=session_id,
            triggered_count=len(triggered),
            triggered_actions=triggered,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}") from e


@router.get("/sessions/{session_id}/reactions/active")
@router.get("/api/v1/sessions/{session_id}/reactions/active")
async def get_active_reaction(session_id: UUID):
    """Retrieve currently active paused reaction interrupt if any."""
    try:
        session = await repo.load(session_id)
        return {
            "session_id": session_id,
            "turn_paused_for_reaction": session.state.turn_paused_for_reaction,
            "active_reaction": session.state.active_reaction,
            "ready_actions": session.state.ready_actions,
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}") from e
