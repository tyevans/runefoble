from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from gateway_api.auth import CurrentPrincipal, get_spicedb_client, require_zanzibar_permission
from gateway_api.character_store import character_store
from gateway_api.dependencies import ws_manager
from gateway_api.models import (
    AdvanceTurnRequest,
    AtmosphereUpdateRequest,
    DMOverrideRequest,
    TokenMoveRequest,
)
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(tags=["Tabletop & Game Sessions"])

DEFAULT_SESSION_PARTICIPANTS: list[dict[str, Any]] = [
    {
        "userId": "user-valeros",
        "username": "Valeros",
        "role": "player",
        "character": "Valeros",
        "characterId": "char-valeros",
        "characterName": "Valeros",
        "characterClass": "Fighter",
        "characterLevel": 4,
        "isReady": False,
        "isAbsent": False,
        "onlineStatus": "online",
        "online": True,
        "ai_stand_in": False,
    },
    {
        "userId": "user-sarah",
        "username": "Sarah",
        "role": "player",
        "character": "Sarah",
        "characterId": "char-sarah",
        "characterName": "Sarah",
        "characterClass": "Rogue",
        "characterLevel": 3,
        "isReady": False,
        "isAbsent": False,
        "onlineStatus": "online",
        "online": True,
        "ai_stand_in": False,
    },
    {
        "userId": "user-kyra",
        "username": "Kyra",
        "role": "player",
        "character": "Kyra",
        "characterId": "char-kyra",
        "characterName": "Kyra",
        "characterClass": "Cleric",
        "characterLevel": 4,
        "isReady": False,
        "isAbsent": False,
        "onlineStatus": "offline",
        "online": False,
        "ai_stand_in": False,
    },
]

DEFAULT_BOARD_TOKENS: list[dict[str, Any]] = [
    {"id": "t1", "name": "Valeros", "x": 2, "y": 2, "color": "#2563eb"},
    {"id": "t2", "name": "Kyra", "x": 3, "y": 3, "color": "#db2777", "is_ai_controlled": True},
]


class HotSwapRequest(BaseModel):
    player_id: str | None = Field(default=None, alias="playerId")
    character_id: str | None = Field(default=None, alias="characterId")

    model_config = ConfigDict(populate_by_name=True)


@router.get(
    "/api/v1/sessions/{session_id}",
    dependencies=[Depends(require_zanzibar_permission("observe", resource_type="session"))],
)
async def get_session_proxy(session_id: str) -> dict:
    """Retrieve game session state, participants, and round index (requires 'observe')."""
    return {
        "id": session_id,
        "campaign_id": ("4" if session_id in {"14", "15"} else session_id),
        "title": f"Session {session_id}",
        "status": ("lobby" if session_id == "15" else "active"),
        "round": 1,
        "current_turn": "c1",
        "participants": DEFAULT_SESSION_PARTICIPANTS,
    }


@router.post(
    "/api/v1/sessions/{session_id}/start",
    dependencies=[Depends(require_zanzibar_permission("control", resource_type="session"))],
)
async def start_session_proxy(session_id: str) -> dict:
    await ws_manager.broadcast(
        {"type": "session_started", "sessionId": session_id, "status": "active"}
    )
    return {"session_id": session_id, "status": "active"}


@router.post(
    "/api/v1/sessions/{session_id}/hot-swap",
    dependencies=[Depends(require_zanzibar_permission("observe", resource_type="session"))],
)
async def hot_swap_session_proxy(
    session_id: str,
    req: HotSwapRequest,
    user: CurrentPrincipal,
) -> dict[str, Any]:
    """Hands off active turn control from AI stand-in to player mid-session."""
    player_id = req.player_id or user.user_id
    char_id = req.character_id or ""

    if char_id:
        spicedb = get_spicedb_client()
        allowed = await spicedb.check_permission(
            resource_type="character",
            resource_id=char_id,
            permission="edit",
            subject_type="user",
            subject_id=player_id,
        )
        if not allowed:
            allowed = await spicedb.check_permission(
                resource_type="session",
                resource_id=session_id,
                permission="observe",
                subject_type="user",
                subject_id=player_id,
            )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User '{player_id}' does not have permission to take control of character '{char_id}'",
            )
        char = character_store.get_character(char_id)
        if char:
            char.is_stand_in_active = False

    payload = {
        "type": "hot_swap_takeover",
        "sessionId": session_id,
        "playerId": player_id,
        "characterId": char_id,
        "status": "control_transferred",
    }
    await ws_manager.broadcast(payload)

    return {
        "session_id": session_id,
        "character_id": char_id,
        "player_id": player_id,
        "status": "control_transferred",
        "is_stand_in_active": False,
    }


@router.post(
    "/api/v1/sessions/{session_id}/turns/advance",
    dependencies=[Depends(require_zanzibar_permission("control", resource_type="session"))],
)
async def advance_turn_proxy(session_id: str, req: AdvanceTurnRequest) -> dict:
    return {
        "session_id": session_id,
        "status": "turn_advanced",
        "active_character_id": req.next_character_id,
    }


@router.post(
    "/api/v1/sessions/{session_id}/dm-override",
    dependencies=[Depends(require_zanzibar_permission("control", resource_type="session"))],
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
    dependencies=[Depends(require_zanzibar_permission("control", resource_type="session"))],
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
    event = {
        "type": "speech_action",
        "speaker": speaker_name,
        "transcript": transcript,
        "action_taken": "Valeros stepped forward 2 squares.",
        "watcher_commentary": "The Watcher observes your advance into the crypt.",
    }
    await ws_manager.broadcast(event)
    return event
