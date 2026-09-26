"""Conversational intent disambiguation router and target candidate matching."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException
from runefoble_events.events import (
    CandidateGhostPreviewEmitted,
    CompoundActionResolved,
    IntentDisambiguationRequested,
)
from the_watcher.dependencies import (
    STREAM_BOARD,
    STREAM_WATCHER,
    compound_action_engine,
    disambiguation_engine,
    get_event_bus,
    logger,
    to_uuid,
)
from the_watcher.models import (
    CandidateTarget,
    CompoundActionNode,
    IntentParseRequest,
    IntentParseResponse,
    IntentResolveRequest,
    IntentResolveResponse,
)

router = APIRouter(tags=["intent"])


async def _safe_publish(bus, stream: str, event) -> None:
    try:
        await bus.publish_event(stream, event)
    except Exception as e:
        logger.warning("Failed to publish %s: %s", type(event).__name__, e)


def evaluate_target_ambiguity(
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
    req: IntentParseRequest,
    ambig_node: CompoundActionNode,
    ambig_candidates: list[CandidateTarget],
    ambig_target: str,
    nodes: list[CompoundActionNode],
    is_compound: bool,
    latency_ms: float,
) -> IntentParseResponse:
    """Generate clarification prompt, register pending state, and dispatch preview events."""
    prompt = disambiguation_engine.generate_clarification_prompt(ambig_target, ambig_candidates)
    pending = disambiguation_engine.register_disambiguation(
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
    bus, s_uuid = get_event_bus(), to_uuid(req.session_id)
    c_uuid = str(to_uuid(req.campaign_id)) if req.campaign_id else None
    await _safe_publish(
        bus,
        STREAM_WATCHER,
        IntentDisambiguationRequested(
            aggregate_id=s_uuid,
            session_id=str(s_uuid),
            campaign_id=c_uuid,
            speaker_id=req.speaker_id,
            speaker_name=req.speaker_name,
            original_transcript=req.transcript,
            disambiguation_id=pending.disambiguation_id,
            action_type=ambig_node.action_type,
            ambiguous_target=ambig_target,
            candidates=[c.model_dump() for c in ambig_candidates],
            clarification_prompt=prompt,
        ),
    )
    for c in ambig_candidates:
        await _safe_publish(
            bus,
            STREAM_BOARD,
            CandidateGhostPreviewEmitted(
                aggregate_id=s_uuid,
                session_id=str(s_uuid),
                disambiguation_id=pending.disambiguation_id,
                candidate_id=c.id,
                token_id=c.id,
                target_x=c.x,
                target_y=c.y,
                descriptor=c.descriptor,
            ),
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
async def resolve_intent_disambiguation(req: IntentResolveRequest) -> IntentResolveResponse:
    """Submit player disambiguation choice and emit resolved compound action graph."""
    t0 = time.perf_counter()
    try:
        pending, m = disambiguation_engine.resolve(
            disambiguation_id=req.disambiguation_id,
            selected_candidate_id=req.selected_candidate_id,
            selected_target=req.selected_target,
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Disambiguation ID '{req.disambiguation_id}' not found or already resolved.",
        ) from None

    status, actions = "ready", pending.actions
    narrative = f"Resolved target to '{m.descriptor}'. Combo actions ready for execution."
    if req.execute_immediately:
        status, actions, narrative, _ = compound_action_engine.execute_plan(
            session_id=req.session_id,
            actions=pending.actions,
            speaker_name=pending.speaker_name,
            step_results=req.step_results,
        )

    bus, s_uuid = get_event_bus(), to_uuid(req.session_id)
    c_uuid = str(to_uuid(req.campaign_id or pending.campaign_id))
    await _safe_publish(
        bus,
        STREAM_WATCHER,
        CompoundActionResolved(
            aggregate_id=s_uuid,
            session_id=str(s_uuid),
            campaign_id=c_uuid,
            speaker_id=req.speaker_id or pending.speaker_id,
            speaker_name=req.speaker_name or pending.speaker_name,
            original_transcript=pending.transcript,
            disambiguation_id=req.disambiguation_id,
            resolved_target=m.descriptor or m.name,
            actions=[a.model_dump() for a in actions],
            status=status,
            narrative_summary=narrative,
        ),
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
