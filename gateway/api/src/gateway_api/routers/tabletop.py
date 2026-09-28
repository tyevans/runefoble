"""Tabletop session, board tokens, and watcher proxy routes for Gateway API."""

from fastapi import APIRouter, Depends
from gateway_api.auth import require_zanzibar_permission
from gateway_api.campaign_store import (
    DEFAULT_BOARD_TOKENS,
    DEFAULT_SESSION_PARTICIPANTS,
    campaign_store,
)
from gateway_api.dependencies import ws_manager
from gateway_api.models import (
    AdvanceTurnRequest,
    AtmosphereUpdateRequest,
    DMOverrideRequest,
    TokenMoveRequest,
)

router = APIRouter(tags=["Tabletop & Game Sessions"])


@router.get(
    "/api/v1/sessions/{session_id}",
    dependencies=[Depends(require_zanzibar_permission("view", resource_type="campaign"))],
)
async def get_session_proxy(session_id: str) -> dict:
    """Retrieve game session state, participants, and round index (requires 'view')."""
    sess = campaign_store.get_session(session_id)
    return {
        "id": session_id,
        "campaign_id": sess.campaign_id if sess else session_id,
        "title": sess.title if sess else f"Session {session_id}",
        "status": sess.status if sess else "active",
        "round": sess.round if sess else 3,
        "current_turn": "c1",
        "participants": DEFAULT_SESSION_PARTICIPANTS,
    }


@router.post(
    "/api/v1/sessions/{session_id}/start",
    dependencies=[Depends(require_zanzibar_permission("run_session", resource_type="campaign"))],
)
async def start_session_proxy(session_id: str) -> dict:
    await ws_manager.broadcast(
        {"type": "session_started", "sessionId": session_id, "status": "active"}
    )
    return {"session_id": session_id, "status": "active"}


@router.post(
    "/api/v1/sessions/{session_id}/turns/advance",
    dependencies=[Depends(require_zanzibar_permission("run_session", resource_type="campaign"))],
)
async def advance_turn_proxy(session_id: str, req: AdvanceTurnRequest) -> dict:
    return {
        "session_id": session_id,
        "status": "turn_advanced",
        "active_character_id": req.next_character_id,
    }


@router.post(
    "/api/v1/sessions/{session_id}/dm-override",
    dependencies=[Depends(require_zanzibar_permission("run_session", resource_type="campaign"))],
)
async def dm_override_proxy(session_id: str, req: DMOverrideRequest) -> dict:
    return {
        "session_id": session_id,
        "status": "override_executed",
        "action": req.action,
        "reason": req.reason,
    }


@router.post(
    "/api/v1/sessions/{session_id}/atmosphere",
    dependencies=[Depends(require_zanzibar_permission("run_session", resource_type="campaign"))],
)
async def update_atmosphere_proxy(session_id: str, req: AtmosphereUpdateRequest) -> dict:
    return {
        "session_id": session_id,
        "status": "atmosphere_updated",
        "atmosphere": req.model_dump(),
    }


@router.post(
    "/api/v1/board/tokens/{token_id}/move",
    dependencies=[Depends(require_zanzibar_permission("move", "board_token", "token_id"))],
)
async def move_token_proxy(token_id: str, req: TokenMoveRequest) -> dict:
    return {"token_id": token_id, "status": "token_moved", "to_x": req.to_x, "to_y": req.to_y}


@router.get(
    "/api/v1/board/tokens/{token_id}",
    dependencies=[Depends(require_zanzibar_permission("inspect", "board_token", "token_id"))],
)
async def get_token_proxy(token_id: str) -> dict:
    return {"token_id": token_id, "status": "active", "x": 2, "y": 3}


@router.get(
    "/api/v1/boards/{session_id}",
    dependencies=[Depends(require_zanzibar_permission("view", resource_type="campaign"))],
)
async def get_board_proxy(session_id: str) -> dict:
    return {"session_id": session_id, "cols": 8, "rows": 8, "tokens": DEFAULT_BOARD_TOKENS}


@router.post("/api/v1/watcher/speak-and-act")
async def speak_and_act(transcript: str, speaker_name: str, session_id: str) -> dict:
    event = {
        "type": "speech_action",
        "speaker": speaker_name,
        "transcript": transcript,
        "action_taken": "Valeros stepped forward 2 squares.",
        "watcher_commentary": "The Watcher observes your advance into the crypt.",
    }
    await ws_manager.broadcast(event)
    return event
