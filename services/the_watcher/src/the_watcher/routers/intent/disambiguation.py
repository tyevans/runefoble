"""Conversational intent disambiguation router and target candidate matching."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from the_watcher.container_access import Disambiguations, Engines
from the_watcher.copilot_state.disambiguations import DisambiguationNotFoundError
from the_watcher.dependencies import require_session_permission
from the_watcher.disambiguation import DisambiguationEngine, DisambiguationStore
from the_watcher.identity import CallerId, get_principal
from the_watcher.models import (
    CandidateTarget,
    CompoundActionNode,
    IntentParseRequest,
    IntentParseResponse,
    IntentResolveRequest,
    IntentResolveResponse,
)

router = APIRouter(dependencies=[Depends(get_principal)], tags=["intent"])


def evaluate_target_ambiguity(
    disambiguation_engine: DisambiguationEngine,
    nodes: list[CompoundActionNode],
    entities: list[dict],
    from_x: int | None = None,
    from_y: int | None = None,
) -> tuple[bool, CompoundActionNode | None, list[CandidateTarget], str]:
    """Evaluate target ambiguity across compound action nodes and match distinguishing tags."""
    has_ambiguity, ambig_node, ambig_candidates, ambig_target = False, None, [], ""
    for node in nodes:
        if not node.target:
            continue
        cands = disambiguation_engine.find_candidates(node.target, entities, from_x, from_y)
        if len(cands) > 1:
            node.requires_disambiguation, node.candidates = True, cands
            if not has_ambiguity:
                has_ambiguity, ambig_node, ambig_candidates, ambig_target = (
                    True,
                    node,
                    cands,
                    node.target,
                )
        elif len(cands) == 1:
            m = cands[0]
            node.target = m.descriptor or m.name
            node.parameters.update(target=node.target, target_id=m.id, target_x=m.x, target_y=m.y)
    return has_ambiguity, ambig_node, ambig_candidates, ambig_target


async def dispatch_disambiguation(
    disambiguation_engine: DisambiguationEngine,
    disambiguation_store: DisambiguationStore,
    req: IntentParseRequest,
    ambig_node: CompoundActionNode,
    ambig_candidates: list[CandidateTarget],
    ambig_target: str,
    nodes: list[CompoundActionNode],
    is_compound: bool,
    latency_ms: float,
) -> IntentParseResponse:
    """Generate clarification prompt, register pending state, and return the choices."""
    prompt = disambiguation_engine.generate_clarification_prompt(ambig_target, ambig_candidates)
    pending = await disambiguation_store.register(
        session_id=req.session_id,
        campaign_id=req.campaign_id,
        speaker_id=req.speaker_id,
        speaker_name=req.speaker_name,
        transcript=req.transcript,
        action_type=ambig_node.action_type,
        ambiguous_target=ambig_target,
        candidates=ambig_candidates,
        clarification_prompt=prompt,
        actions=nodes,
    )
    return IntentParseResponse(
        session_id=req.session_id,
        speaker_name=req.speaker_name,
        transcript=req.transcript,
        requires_disambiguation=True,
        disambiguation_id=pending.disambiguation_id,
        clarification_prompt=prompt,
        candidates=ambig_candidates,
        is_compound=is_compound,
        actions=nodes,
        execution_latency_ms=latency_ms,
    )


@router.post("/api/v1/watcher/intent/resolve", response_model=IntentResolveResponse)
async def resolve_intent_disambiguation(
    engines: Engines,
    disambiguations: Disambiguations,
    caller_id: CallerId,
    req: IntentResolveRequest,
) -> IntentResolveResponse:
    """Submit player disambiguation choice and emit resolved compound action graph."""
    await require_session_permission(caller_id, req.session_id, "session.participate")
    t0 = time.perf_counter()
    try:
        pending, m = await disambiguations.resolve(
            session_id=req.session_id,
            disambiguation_id=req.disambiguation_id,
            selected_candidate_id=req.selected_candidate_id,
            selected_target=req.selected_target,
        )
    except DisambiguationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Disambiguation ID '{req.disambiguation_id}' not found or already resolved.",
        ) from None

    status, actions = "ready", pending.actions
    narrative = f"Resolved target to '{m.descriptor}'. Combo actions ready for execution."
    if req.execute_immediately:
        status, actions, narrative, _ = engines.compound_actions.execute_plan(
            session_id=req.session_id,
            actions=pending.actions,
            speaker_name=pending.speaker_name,
            step_results=req.step_results,
        )

    return IntentResolveResponse(
        session_id=req.session_id,
        disambiguation_id=req.disambiguation_id,
        resolved_target=m.descriptor or m.name,
        status=status,
        actions=actions,
        narrative_summary=narrative,
        execution_latency_ms=(time.perf_counter() - t0) * 1000,
    )
