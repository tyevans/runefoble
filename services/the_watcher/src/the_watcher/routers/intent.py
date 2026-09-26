"""Intent parsing and speech-to-intent routes for The Watcher service."""

from __future__ import annotations

import httpx
from fastapi import APIRouter
from runefoble_events.events import (
    SpeechIntentParsed,
    TokenMoved,
    WatcherNarrationGenerated,
)
from the_watcher.dependencies import (
    INFERENCE_URL,
    STREAM_BOARD,
    STREAM_WATCHER,
    engine,
    get_event_bus,
    logger,
    to_uuid,
)
from the_watcher.models import IntentResult, SpeechInputRequest

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
