"""Single speech-to-intent parsing and event dispatch router."""

from __future__ import annotations

from fastapi import APIRouter
from runefoble_events.events import (
    SpeechIntentParsed,
    TokenMoved,
    WatcherNarrationGenerated,
)
from runefoble_platform.event_publish import publish_best_effort
from the_watcher.board_client import fetch_visible_tokens
from the_watcher.dependencies import (
    BOARD_STATE_URL,
    INFERENCE_URL,
    STREAM_BOARD,
    STREAM_WATCHER,
    engine,
    get_event_bus,
    to_uuid,
)
from the_watcher.models import (
    IntentResult,
    SpeechInputRequest,
)
from the_watcher.worker_client import call_worker

router = APIRouter(tags=["intent"])


async def _parse_with_worker(req: SpeechInputRequest) -> IntentResult:
    """Parse speech with the inference worker. The worker receives the session's visible tokens.

    A worker or board state failure is raised as HTTP 503. It is never replaced by a template.
    """
    visible_tokens = await fetch_visible_tokens(BOARD_STATE_URL, req.session_id)
    data = await call_worker(
        INFERENCE_URL,
        "/inference/v1/intent",
        {
            "campaign_id": req.campaign_id,
            "session_id": req.session_id,
            "speaker_id": req.speaker_id,
            "speaker_name": req.speaker_name,
            "transcript": req.transcript,
            "visible_tokens": visible_tokens,
        },
        timeout=2.0,
    )
    action = data["action"]
    target_name = action.get("target_token_name") or action.get("target_token_id")
    return IntentResult(
        action_type=action["action_type"],
        confidence=action.get("confidence"),
        parameters=action,
        target=target_name,
        details=action.get("narrative_flavor", req.transcript),
        watcher_reply=action.get("narrative_flavor", ""),
        source=data["source"],
        degraded=data["degraded"],
    )


@router.post("/api/v1/watcher/transcribe-and-act", response_model=IntentResult)
@router.post("/api/v1/watcher/intent", response_model=IntentResult)
async def process_speech_action(req: SpeechInputRequest) -> IntentResult:
    """Parse player speech, translate to game action, dispatch events, and trigger board state update."""
    intent: IntentResult | None = None

    if INFERENCE_URL:
        intent = await _parse_with_worker(req)

    if intent is None:
        intent = engine.parse_speech_intent(req.transcript, req.speaker_name)

    bus = get_event_bus()
    session_uuid = to_uuid(req.session_id)
    campaign_uuid = to_uuid(req.campaign_id)

    target_val = (
        intent.target or intent.parameters.get("target") or intent.parameters.get("target_token")
    )

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

    narration_event = WatcherNarrationGenerated(
        aggregate_id=session_uuid,
        session_id=session_uuid,
        campaign_id=campaign_uuid,
        narrative_text=intent.watcher_reply,
        tone="tactical" if intent.action_type in ("move", "attack") else "dark_fantasy",
    )

    await publish_best_effort(bus, STREAM_WATCHER, speech_intent_event)
    await publish_best_effort(bus, STREAM_WATCHER, narration_event)

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
        await publish_best_effort(bus, STREAM_BOARD, token_moved_event)

    return intent
