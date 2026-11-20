"""Single speech-to-intent parsing and event dispatch router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from runefoble_events.events import (
    SpeechIntentParsed,
)
from runefoble_platform.event_publish import publish_best_effort
from runefoble_platform.identifiers import opaque_aggregate_id
from the_watcher.board_client import fetch_visible_tokens
from the_watcher.board_preview import propose_move_preview
from the_watcher.container_access import Engines, EventBus
from the_watcher.dependencies import STREAM_WATCHER, require_session_permission, require_speaker
from the_watcher.engine_selection import WatcherEngineSettings, load_watcher_ports
from the_watcher.identity import CallerId, get_principal
from the_watcher.models import (
    IntentResult,
    SpeechInputRequest,
)
from the_watcher.move_destination import (
    check_in_grid,
    check_origin,
    coordinate_target,
    named_target,
    resolve_named_target,
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
    authorization = request.headers.get("authorization")
    intent = await load_watcher_ports(engines.watcher).intent.parse(req, authorization)

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
    """Send the move to board_state as a proposal. The board commits nothing until confirm.

    Every check runs before the proposal is sent. A failed check stages no preview (TASK-0942).
    """
    authorization = request.headers.get("authorization")
    if not authorization:
        raise HTTPException(status_code=401, detail="A bearer token is required to propose a move")
    origin = check_origin(req.from_x, req.from_y)
    to_x, to_y = await _destination(req, intent, origin, authorization, engine_)
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


async def _destination(
    req: SpeechInputRequest,
    intent: IntentResult,
    origin: tuple[int, int],
    authorization: str,
    engine_: TheWatcherEngine,
) -> tuple[int, int]:
    """Choose the destination cell. The order is named token, then coordinates, then distance.

    An intent with none of these keys has no destination. That is a client error (422), never
    a zero-length move.
    """
    params = intent.parameters
    names, token_id = named_target(params)
    if names or token_id:
        tokens = await fetch_visible_tokens(
            WatcherEngineSettings().board_state_url, req.session_id, authorization
        )
        return resolve_named_target(names, token_id, tokens, origin, req.grid_cols, req.grid_rows)
    if (cell := coordinate_target(params)) is not None:
        return check_in_grid(cell, req.grid_cols, req.grid_rows)
    if "dx" in params or "dy" in params:
        return engine_.calculate_bounded_destination(
            origin[0],
            origin[1],
            params.get("dx", 0),
            params.get("dy", 0),
            cols=req.grid_cols,
            rows=req.grid_rows,
        )
    raise HTTPException(
        status_code=422,
        detail="A move needs a destination: a named token, coordinates or a distance.",
    )
