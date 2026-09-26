import time

import httpx
from fastapi import APIRouter, HTTPException
from runefoble_events.events import (
    CandidateGhostPreviewEmitted,
    CompoundActionResolved,
    IntentDisambiguationRequested,
    SpeechIntentParsed,
    TokenMoved,
    WatcherNarrationGenerated,
)
from the_watcher.dependencies import (
    INFERENCE_URL,
    STREAM_BOARD,
    STREAM_WATCHER,
    compound_action_engine,
    disambiguation_engine,
    engine,
    get_event_bus,
    logger,
    to_uuid,
)
from the_watcher.models import (
    CandidateTarget,
    CompoundActionNode,
    IntentExecuteRequest,
    IntentExecuteResponse,
    IntentParseRequest,
    IntentParseResponse,
    IntentResolveRequest,
    IntentResolveResponse,
    IntentResult,
    SpeechInputRequest,
)

router = APIRouter(tags=["intent"])


@router.post("/api/v1/watcher/transcribe-and-act", response_model=IntentResult)
@router.post("/api/v1/watcher/intent", response_model=IntentResult)
async def process_speech_action(req: SpeechInputRequest) -> IntentResult:
    """Parse player speech, translate to game action, dispatch events, and trigger board state update."""
    intent: IntentResult | None = None

    if INFERENCE_URL:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.post(
                    f"{INFERENCE_URL}/inference/v1/intent",
                    json={
                        "campaign_id": req.campaign_id,
                        "session_id": req.session_id,
                        "speaker_id": req.speaker_id,
                        "speaker_name": req.speaker_name,
                        "transcript": req.transcript,
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    action = data.get("action", {})
                    target_name = action.get("target_token_name") or action.get("target_token_id")
                    intent = IntentResult(
                        action_type=action.get("action_type", "unknown"),
                        confidence=action.get("confidence", 0.9),
                        parameters=action,
                        target=target_name,
                        details=action.get("narrative_flavor", req.transcript),
                        watcher_reply=action.get("narrative_flavor")
                        or f"The Watcher acknowledges {req.speaker_name}.",
                    )
        except Exception as e:
            logger.warning("Inference worker failed: %s. Falling back to local engine.", e)

    if intent is None:
        intent = engine.parse_speech_intent(req.transcript, req.speaker_name)

    # Dispatch domain events across Redis Streams
    bus = get_event_bus()
    session_uuid = to_uuid(req.session_id)
    campaign_uuid = to_uuid(req.campaign_id)

    target_val = (
        intent.target or intent.parameters.get("target") or intent.parameters.get("target_token")
    )

    # 1. Dispatch SpeechIntentParsed to runefoble.events.watcher
    speech_intent_event = SpeechIntentParsed(
        aggregate_id=session_uuid,
        session_id=session_uuid,
        campaign_id=campaign_uuid,
        speaker_name=req.speaker_name,
        action_type=intent.action_type,
        target=target_val,
        confidence=intent.confidence,
        flavor_text=intent.watcher_reply,
        raw_transcript=req.transcript,
    )

    # 2. Dispatch WatcherNarrationGenerated to runefoble.events.watcher
    narration_event = WatcherNarrationGenerated(
        aggregate_id=session_uuid,
        session_id=session_uuid,
        campaign_id=campaign_uuid,
        narrative_text=intent.watcher_reply,
        tone="tactical" if intent.action_type in ("move", "attack") else "dark_fantasy",
    )

    try:
        await bus.publish_event(STREAM_WATCHER, speech_intent_event)
        await bus.publish_event(STREAM_WATCHER, narration_event)
    except Exception as e:
        logger.warning(
            "Failed to publish watcher events to Redis stream '%s': %s", STREAM_WATCHER, e
        )

    # 3. If action is movement, dispatch TokenMoved to runefoble.events.board
    if intent.action_type == "move":
        from_x = req.from_x if req.from_x is not None else 0
        from_y = req.from_y if req.from_y is not None else 0

        if "to_x" in intent.parameters and "to_y" in intent.parameters:
            to_x = int(intent.parameters["to_x"])
            to_y = int(intent.parameters["to_y"])
        else:
            dx = intent.parameters.get("dx", 0)
            dy = intent.parameters.get("dy", 0)
            to_x, to_y = engine.calculate_bounded_destination(
                from_x, from_y, dx, dy, cols=req.grid_cols, rows=req.grid_rows
            )

        token_id = req.token_id or f"token-{req.speaker_name.lower().replace(' ', '-')}"
        token_moved_event = TokenMoved(
            aggregate_id=session_uuid,
            session_id=session_uuid,
            campaign_id=campaign_uuid,
            token_id=token_id,
            name=req.speaker_name,
            from_x=from_x,
            from_y=from_y,
            to_x=to_x,
            to_y=to_y,
            initiated_by="player",
        )
        try:
            await bus.publish_event(STREAM_BOARD, token_moved_event)
        except Exception as e:
            logger.warning(
                "Failed to publish TokenMoved event to Redis stream '%s': %s", STREAM_BOARD, e
            )

    return intent


@router.post("/api/v1/watcher/intent/parse", response_model=IntentParseResponse)
async def parse_intent_and_disambiguate(req: IntentParseRequest) -> IntentParseResponse:
    """Parse player speech, decompose compound actions, and evaluate target disambiguation."""
    t0 = time.perf_counter()
    entities = req.entities or req.tokens or []

    is_compound, nodes = compound_action_engine.decompose(req.transcript, req.speaker_name)

    # Evaluate target ambiguity across each action node
    has_ambiguity = False
    ambig_node: CompoundActionNode | None = None
    ambig_candidates: list[CandidateTarget] = []
    ambig_target: str = ""

    for node in nodes:
        if node.target:
            candidates = disambiguation_engine.find_candidates(
                target_phrase=node.target,
                entities=entities,
                from_x=req.from_x,
                from_y=req.from_y,
            )
            if len(candidates) > 1:
                node.requires_disambiguation = True
                node.candidates = candidates
                if not has_ambiguity:
                    has_ambiguity = True
                    ambig_node = node
                    ambig_candidates = candidates
                    ambig_target = node.target
            elif len(candidates) == 1:
                # Disambiguated uniquely by distinguishing tags
                matched = candidates[0]
                node.target = matched.descriptor or matched.name
                node.parameters["target"] = matched.descriptor or matched.name
                node.parameters["target_id"] = matched.id
                node.parameters["target_x"] = matched.x
                node.parameters["target_y"] = matched.y

    latency_ms = (time.perf_counter() - t0) * 1000

    if has_ambiguity and ambig_node is not None:
        clarification = disambiguation_engine.generate_clarification_prompt(
            ambig_target, ambig_candidates
        )
        pending = disambiguation_engine.register_disambiguation(
            session_id=req.session_id,
            campaign_id=req.campaign_id,
            speaker_id=req.speaker_id,
            speaker_name=req.speaker_name,
            transcript=req.transcript,
            action_type=ambig_node.action_type,
            ambiguous_target=ambig_target,
            candidates=ambig_candidates,
            clarification_prompt=clarification,
            actions=nodes,
        )

        bus = get_event_bus()
        session_uuid = to_uuid(req.session_id)
        campaign_uuid = to_uuid(req.campaign_id) if req.campaign_id else None

        # 1. Publish IntentDisambiguationRequested to runefoble.events.watcher
        disambig_event = IntentDisambiguationRequested(
            aggregate_id=session_uuid,
            session_id=str(session_uuid),
            campaign_id=str(campaign_uuid) if campaign_uuid else None,
            speaker_id=req.speaker_id,
            speaker_name=req.speaker_name,
            original_transcript=req.transcript,
            disambiguation_id=pending.disambiguation_id,
            action_type=ambig_node.action_type,
            ambiguous_target=ambig_target,
            candidates=[c.model_dump() for c in ambig_candidates],
            clarification_prompt=clarification,
        )
        try:
            await bus.publish_event(STREAM_WATCHER, disambig_event)
        except Exception as e:
            logger.warning(
                "Failed to publish IntentDisambiguationRequested to %s: %s", STREAM_WATCHER, e
            )

        # 2. Publish ghost preview candidate events to runefoble.events.board
        for c in ambig_candidates:
            ghost_event = CandidateGhostPreviewEmitted(
                aggregate_id=session_uuid,
                session_id=str(session_uuid),
                disambiguation_id=pending.disambiguation_id,
                candidate_id=c.id,
                token_id=c.id,
                target_x=c.x,
                target_y=c.y,
                descriptor=c.descriptor,
            )
            try:
                await bus.publish_event(STREAM_BOARD, ghost_event)
            except Exception as e:
                logger.warning(
                    "Failed to publish CandidateGhostPreviewEmitted to %s: %s", STREAM_BOARD, e
                )

        return IntentParseResponse(
            session_id=req.session_id,
            speaker_name=req.speaker_name,
            transcript=req.transcript,
            requires_disambiguation=True,
            disambiguation_id=pending.disambiguation_id,
            clarification_prompt=clarification,
            candidates=ambig_candidates,
            is_compound=is_compound,
            actions=nodes,
            execution_latency_ms=latency_ms,
        )

    # No disambiguation needed
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


@router.post("/api/v1/watcher/intent/resolve", response_model=IntentResolveResponse)
async def resolve_intent_disambiguation(req: IntentResolveRequest) -> IntentResolveResponse:
    """Submit player disambiguation choice and emit resolved compound action graph."""
    t0 = time.perf_counter()

    try:
        pending, matched_candidate = disambiguation_engine.resolve(
            disambiguation_id=req.disambiguation_id,
            selected_candidate_id=req.selected_candidate_id,
            selected_target=req.selected_target,
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Disambiguation ID '{req.disambiguation_id}' not found or already resolved.",
        ) from None

    status = "ready"
    actions = pending.actions
    narrative = (
        f"Resolved target to '{matched_candidate.descriptor}'. Combo actions ready for execution."
    )

    if req.execute_immediately:
        status, actions, narrative, _failed_id = compound_action_engine.execute_plan(
            session_id=req.session_id,
            actions=pending.actions,
            speaker_name=pending.speaker_name,
            step_results=req.step_results,
        )

    # Publish CompoundActionResolved to runefoble.events.watcher
    bus = get_event_bus()
    session_uuid = to_uuid(req.session_id)
    campaign_uuid = to_uuid(req.campaign_id or pending.campaign_id)

    resolved_event = CompoundActionResolved(
        aggregate_id=session_uuid,
        session_id=str(session_uuid),
        campaign_id=str(campaign_uuid) if campaign_uuid else None,
        speaker_id=req.speaker_id or pending.speaker_id,
        speaker_name=req.speaker_name or pending.speaker_name,
        original_transcript=pending.transcript,
        disambiguation_id=req.disambiguation_id,
        resolved_target=matched_candidate.descriptor or matched_candidate.name,
        actions=[a.model_dump() for a in actions],
        status=status,
        narrative_summary=narrative,
    )
    try:
        await bus.publish_event(STREAM_WATCHER, resolved_event)
    except Exception as e:
        logger.warning("Failed to publish CompoundActionResolved to %s: %s", STREAM_WATCHER, e)

    latency_ms = (time.perf_counter() - t0) * 1000

    return IntentResolveResponse(
        session_id=req.session_id,
        disambiguation_id=req.disambiguation_id,
        resolved_target=matched_candidate.descriptor or matched_candidate.name,
        status=status,
        actions=actions,
        narrative_summary=narrative,
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
