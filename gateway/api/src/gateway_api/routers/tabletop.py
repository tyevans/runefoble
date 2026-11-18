from typing import Any

from fastapi import APIRouter, Depends
from gateway_api.auth import CurrentPrincipal, require_zanzibar_permission
from gateway_api.dependencies import ws_manager
from gateway_api.models import TokenMoveRequest
from gateway_api.session_access import require_session_permission

router = APIRouter(tags=["Tabletop & Game Sessions"])

DEFAULT_BOARD_TOKENS: list[dict[str, Any]] = [
    {"id": "t1", "name": "Valeros", "x": 2, "y": 2, "color": "#2563eb"},
    {"id": "t2", "name": "Kyra", "x": 3, "y": 3, "color": "#db2777", "is_ai_controlled": True},
]


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
    dependencies=[Depends(require_zanzibar_permission("observe", resource_type="session"))],
)
async def get_board_proxy(session_id: str) -> dict:
    return {"session_id": session_id, "cols": 8, "rows": 8, "tokens": DEFAULT_BOARD_TOKENS}


@router.post("/api/v1/watcher/speak-and-act")
async def speak_and_act(
    transcript: str,
    speaker_name: str,
    session_id: str,
    user: CurrentPrincipal,
) -> dict:
    await require_session_permission(session_id, user.user_id, "participate")
    event = {
        "type": "speech_action",
        "speaker": speaker_name,
        "transcript": transcript,
        "action_taken": "Valeros stepped forward 2 squares.",
        "watcher_commentary": "The Watcher observes your advance into the crypt.",
    }
    await ws_manager.broadcast(session_id, event)
    return event
