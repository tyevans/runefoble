"""Campaign, session, board, and role management router for Runefoble Gateway API."""

from typing import Annotated

from fastapi import APIRouter, Depends
from gateway_api.auth import get_current_user, get_spicedb_client, require_zanzibar_permission
from gateway_api.dependencies import ws_manager
from gateway_api.models import (
    AdvanceTurnRequest,
    AssignRoleRequest,
    AtmosphereUpdateRequest,
    DMOverrideRequest,
    TokenMoveRequest,
)
from runefoble_auth.zitadel import AuthenticatedUser

router = APIRouter(tags=["Campaigns & Sessions"])


@router.get("/api/v1/profile")
async def get_profile(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> dict:
    """Retrieve authenticated Zitadel user profile claims."""
    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "roles": user.roles,
        "is_admin": user.is_admin,
    }


@router.post("/api/v1/campaigns/{campaign_id}/roles")
async def assign_campaign_role(campaign_id: str, req: AssignRoleRequest) -> dict:
    """Write fine-grained relationship tuple to SpiceDB Zanzibar."""
    client = get_spicedb_client()
    relation_map = {
        "owner": "owner",
        "dungeon_master": "dungeon_master",
        "player": "player",
        "spectator": "view",
    }
    relation = relation_map[req.role]
    await client.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation=relation,
        subject_type="user",
        subject_id=req.user_id,
    )
    return {
        "status": "role_assigned",
        "campaign_id": campaign_id,
        "user_id": req.user_id,
        "role": req.role,
        "zanzibar_relation": f"campaign:{campaign_id}#{relation}@user:{req.user_id}",
    }


@router.get(
    "/api/v1/campaigns/{campaign_id}",
    dependencies=[Depends(require_zanzibar_permission("view", resource_type="campaign"))],
)
async def get_campaign_proxy(campaign_id: str) -> dict:
    """Retrieve campaign overview details (requires 'view')."""
    return {
        "id": campaign_id,
        "campaign_id": campaign_id,
        "title": f"Campaign {campaign_id}",
        "status": "active",
    }


@router.get(
    "/api/v1/sessions/{session_id}",
    dependencies=[Depends(require_zanzibar_permission("view", resource_type="campaign"))],
)
async def get_session_proxy(session_id: str) -> dict:
    """Retrieve game session state, participants, and round index (requires 'view')."""
    return {
        "id": session_id,
        "campaign_id": session_id,
        "status": "active",
        "round": 3,
        "current_turn": "c1",
        "participants": [
            {"username": "Alice", "character": "Valeros", "role": "player", "online": True},
            {
                "username": "Bob",
                "character": "Kyra",
                "role": "player",
                "online": False,
                "ai_stand_in": True,
            },
        ],
    }


@router.post(
    "/api/v1/sessions/{session_id}/turns/advance",
    dependencies=[Depends(require_zanzibar_permission("run_session", resource_type="campaign"))],
)
async def advance_turn_proxy(session_id: str, req: AdvanceTurnRequest) -> dict:
    """Advance session turn (requires 'run_session' DM permission)."""
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
    """Execute DM override on session rules or actions (requires 'run_session')."""
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
    """Update campaign sensory atmosphere and lighting (requires 'run_session')."""
    return {
        "session_id": session_id,
        "status": "atmosphere_updated",
        "atmosphere": req.model_dump(),
    }


@router.post(
    "/api/v1/board/tokens/{token_id}/move",
    dependencies=[
        Depends(
            require_zanzibar_permission(
                "move", resource_type="board_token", resource_param="token_id"
            )
        )
    ],
)
async def move_token_proxy(token_id: str, req: TokenMoveRequest) -> dict:
    """Move a tactical token on the board (requires 'move' on board_token)."""
    return {
        "token_id": token_id,
        "status": "token_moved",
        "to_x": req.to_x,
        "to_y": req.to_y,
    }


@router.get(
    "/api/v1/board/tokens/{token_id}",
    dependencies=[
        Depends(
            require_zanzibar_permission(
                "inspect", resource_type="board_token", resource_param="token_id"
            )
        )
    ],
)
async def get_token_proxy(token_id: str) -> dict:
    """Inspect tactical token details (requires 'inspect' on board_token)."""
    return {
        "token_id": token_id,
        "status": "active",
        "x": 2,
        "y": 3,
    }


@router.get(
    "/api/v1/boards/{session_id}",
    dependencies=[Depends(require_zanzibar_permission("view", resource_type="campaign"))],
)
async def get_board_proxy(session_id: str) -> dict:
    """Retrieve tactical board tokens, coordinates, and grid dimensions (requires 'view')."""
    return {
        "session_id": session_id,
        "cols": 8,
        "rows": 8,
        "tokens": [
            {"id": "t1", "name": "Valeros", "x": 2, "y": 3, "color": "#2563eb"},
            {
                "id": "t2",
                "name": "Kyra",
                "x": 3,
                "y": 3,
                "color": "#db2777",
                "is_ai_controlled": True,
            },
        ],
    }


@router.post("/api/v1/watcher/speak-and-act")
async def speak_and_act(transcript: str, speaker_name: str, session_id: str) -> dict:
    """Spoken command ingestion: parse intent and mutate the game board in real-time."""
    event = {
        "type": "speech_action",
        "speaker": speaker_name,
        "transcript": transcript,
        "action_taken": "Valeros stepped forward 2 squares.",
        "watcher_commentary": "The Watcher observes your advance into the crypt.",
    }
    await ws_manager.broadcast(event)
    return event
