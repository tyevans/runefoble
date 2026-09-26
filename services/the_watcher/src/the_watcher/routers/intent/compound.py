"""Compound action combo decomposition, sequential execution, and rollback handling router."""

from __future__ import annotations

import time

from fastapi import APIRouter
from the_watcher.dependencies import (
    compound_action_engine,
    engine,
)
from the_watcher.models import (
    IntentExecuteRequest,
    IntentExecuteResponse,
    IntentParseRequest,
    IntentParseResponse,
)
from the_watcher.routers.intent.disambiguation import (
    dispatch_disambiguation,
    evaluate_target_ambiguity,
)

router = APIRouter(tags=["intent"])


@router.post("/api/v1/watcher/intent/parse", response_model=IntentParseResponse)
async def parse_intent_and_disambiguate(req: IntentParseRequest) -> IntentParseResponse:
    """Parse player speech, decompose compound actions, and evaluate target disambiguation."""
    t0 = time.perf_counter()
    entities = req.entities or req.tokens or []

    is_compound, nodes = compound_action_engine.decompose(req.transcript, req.speaker_name)
    has_ambiguity, ambig_node, ambig_candidates, ambig_target = evaluate_target_ambiguity(
        nodes=nodes, entities=entities, from_x=req.from_x, from_y=req.from_y
    )

    latency_ms = (time.perf_counter() - t0) * 1000

    if has_ambiguity and ambig_node is not None:
        return await dispatch_disambiguation(
            req=req,
            ambig_node=ambig_node,
            ambig_candidates=ambig_candidates,
            ambig_target=ambig_target,
            nodes=nodes,
            is_compound=is_compound,
            latency_ms=latency_ms,
        )

    single_intent = None
    if not is_compound and len(nodes) == 1:
        single_intent = engine.parse_speech_intent(req.transcript, req.speaker_name)

    return IntentParseResponse(
        session_id=req.session_id,
        speaker_name=req.speaker_name,
        transcript=req.transcript,
        requires_disambiguation=False,
        is_compound=is_compound,
        actions=nodes,
        single_intent=single_intent,
        execution_latency_ms=latency_ms,
    )


@router.post("/api/v1/watcher/intent/execute", response_model=IntentExecuteResponse)
async def execute_compound_actions(req: IntentExecuteRequest) -> IntentExecuteResponse:
    """Execute compound action combo step-by-step with partial failure and rollback handling."""
    status, updated_actions, narrative, failed_id = compound_action_engine.execute_plan(
        session_id=req.session_id,
        actions=req.actions,
        speaker_name=req.speaker_name,
        step_results=req.step_results,
        rollback_on_failure=req.rollback_on_failure,
    )

    return IntentExecuteResponse(
        session_id=req.session_id,
        status=status,
        actions=updated_actions,
        narrative_summary=narrative,
        failed_node_id=failed_id,
    )
