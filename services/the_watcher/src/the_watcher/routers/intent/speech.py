"""Single speech-to-intent parsing and event dispatch router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from runefoble_events.events import (
    SpeechIntentParsed,
)
from runefoble_platform.event_publish import publish_best_effort
from runefoble_platform.identifiers import opaque_aggregate_id
from the_watcher.board_preview import propose_move_preview
from the_watcher.container_access import Engines, EventBus
from the_watcher.dependencies import STREAM_WATCHER, require_session_permission, require_speaker
from the_watcher.engine_selection import WatcherEngineSettings, load_watcher_ports
from the_watcher.identity import CallerId, get_principal
from the_watcher.models import (
    IntentResult,
    SpeechInputRequest,
)
from the_watcher.watcher_ai import TheWatcherEngine

router = APIRouter(dependencies=[Depends(get_principal)], tags=["intent"])


@router.post("/api/v1/watcher/transcribe-and-act", response_model=IntentResult)
async def process_speech_action(
    engines: Engines,
    event_bus: EventBus,
    caller_id: CallerId,
    req: SpeechInputRequest,
    request: Request,
) -> IntentResult:
    """Parse player speech and propose a move as a ghost preview. Only player confirm commits it."""
    await require_session_permission(caller_id, req.session_id, "session.participate")
    await require_speaker(caller_id, req.speaker_id)
    intent = await load_watcher_ports(engines.watcher).intent.parse(req)

    bus = event_bus.get()
    session_uuid = opaque_aggregate_id(req.session_id, field="session_id")
    campaign_uuid = opaque_aggregate_id(req.campaign_id, field="campaign_id")

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

    await publish_best_effort(bus, STREAM_WATCHER, speech_intent_event)

    if intent.action_type == "move":
        await _propose_move(request, req, intent, engines.watcher)

    return intent


async def _propose_move(
    request: Request, req: SpeechInputRequest, intent: IntentResult, engine_: TheWatcherEngine
) -> None:
    """Send the move to board_state as a proposal. The board commits nothing until confirm."""
    authorization = request.headers.get("authorization")
    if not authorization:
        raise HTTPException(status_code=401, detail="A bearer token is required to propose a move")
    from_x = req.from_x if req.from_x is not None else 0
    from_y = req.from_y if req.from_y is not None else 0
    if "to_x" in intent.parameters and "to_y" in intent.parameters:
        to_x = int(intent.parameters["to_x"])
        to_y = int(intent.parameters["to_y"])
    else:
        dx = intent.parameters.get("dx", 0)
        dy = intent.parameters.get("dy", 0)
        to_x, to_y = engine_.calculate_bounded_destination(
            from_x, from_y, dx, dy, cols=req.grid_cols, rows=req.grid_rows
        )
    await propose_move_preview(
        WatcherEngineSettings().board_state_url,
        authorization,
        req.session_id,
        {
            "token_id": req.token_id,
            "speaker_name": req.speaker_name,
            "raw_transcript": req.transcript,
            "to_x": to_x,
            "to_y": to_y,
            "from_x": req.from_x,
            "from_y": req.from_y,
        },
    )
