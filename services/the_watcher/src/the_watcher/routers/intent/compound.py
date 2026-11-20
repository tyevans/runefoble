"""Compound action combo decomposition, sequential execution, and rollback handling router.

Routing (ADR-0022): the multi-node parse (`actions`) stays on the grammar and a node never
reaches the worker. The single-intent result comes from the intent port, so it follows the same
grammar-first rule as the speech route.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request
from the_watcher.container_access import Disambiguations, Engines
from the_watcher.dependencies import require_character_permission, require_session_permission
from the_watcher.engine_selection import load_watcher_ports
from the_watcher.identity import CallerId, get_principal
from the_watcher.models import (
    IntentExecuteRequest,
    IntentExecuteResponse,
    IntentParseRequest,
    IntentParseResponse,
    SpeechInputRequest,
)
from the_watcher.routers.intent.disambiguation import (
    dispatch_disambiguation,
    evaluate_target_ambiguity,
)

router = APIRouter(dependencies=[Depends(get_principal)], tags=["intent"])


@router.post("/api/v1/watcher/intent/parse", response_model=IntentParseResponse)
async def parse_intent_and_disambiguate(
    engines: Engines,
    disambiguations: Disambiguations,
    caller_id: CallerId,
    req: IntentParseRequest,
    request: Request,
) -> IntentParseResponse:
    """Parse player speech, decompose compound actions, and evaluate target disambiguation."""
    await require_session_permission(caller_id, req.session_id, "session.participate")
    t0 = time.perf_counter()
    entities = req.entities or req.tokens or []

    is_compound, nodes = engines.compound_actions.decompose(req.transcript, req.speaker_name)
    has_ambiguity, ambig_node, ambig_candidates, ambig_target = evaluate_target_ambiguity(
        engines.disambiguation, nodes=nodes, entities=entities, from_x=req.from_x, from_y=req.from_y
    )

    latency_ms = (time.perf_counter() - t0) * 1000

    if has_ambiguity and ambig_node is not None:
        return await dispatch_disambiguation(
            engines.disambiguation,
            disambiguations,
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
        single_intent = await load_watcher_ports(engines.watcher).intent.parse(
            _speech_request(req), request.headers.get("authorization")
        )

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


def _speech_request(req: IntentParseRequest) -> SpeechInputRequest:
    """The intent port reads the speech fields. An absent campaign id is sent as an empty string."""
    return SpeechInputRequest(
        speaker_id=req.speaker_id,
        speaker_name=req.speaker_name,
        transcript=req.transcript,
        session_id=req.session_id,
        campaign_id=req.campaign_id or "",
        token_id=req.token_id,
        from_x=req.from_x,
        from_y=req.from_y,
        grid_cols=req.grid_cols,
        grid_rows=req.grid_rows,
    )


@router.post("/api/v1/watcher/intent/execute", response_model=IntentExecuteResponse)
async def execute_compound_actions(
    engines: Engines, caller_id: CallerId, req: IntentExecuteRequest
) -> IntentExecuteResponse:
    """Execute compound action combo step-by-step with partial failure and rollback handling."""
    await require_session_permission(caller_id, req.session_id, "session.participate")
    for node in req.actions:
        # A node that names its acting character must pass character.edit for that character.
        character_id = node.parameters.get("character_id")
        if character_id:
            await require_character_permission(caller_id, character_id, "character.edit")
    status, updated_actions, narrative, failed_id = engines.compound_actions.execute_plan(
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
