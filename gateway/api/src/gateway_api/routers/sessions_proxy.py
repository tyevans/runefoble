"""Tabletop session routes proxied to game_session, which owns session state (TASK-0581).

The gateway keeps the public paths and the Zanzibar check on each route. It forwards the
caller's bearer token, so game_session verifies the caller again and applies the state change.
The gateway stores no session state. A failed upstream call returns the mapping in
`upstream_errors.py`: 503 when unreachable, 502 on upstream 5xx, upstream 4xx unchanged.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from gateway_api.auth import require_zanzibar_permission
from gateway_api.dependencies import ws_manager
from gateway_api.models import AtmosphereUpdateRequest, DMOverrideRequest
from gateway_api.proxy import forward_json
from pydantic import BaseModel, ConfigDict, Field

SERVICE = "game_session"
SESSIONS = "/api/v1/sessions"

router = APIRouter(tags=["Tabletop & Game Sessions"])


class HotSwapRequest(BaseModel):
    character_id: UUID = Field(alias="characterId")

    model_config = ConfigDict(populate_by_name=True)


@router.get(
    "/api/v1/sessions/{session_id}",
    dependencies=[Depends(require_zanzibar_permission("observe", resource_type="session"))],
)
async def get_session_proxy(session_id: str, request: Request) -> Any:
    """Read session state, participants, and turn index (requires 'observe'; game_session)."""
    return await forward_json(
        request, service=SERVICE, method="GET", path=f"{SESSIONS}/{session_id}"
    )


@router.post(
    "/api/v1/sessions/{session_id}/start",
    dependencies=[Depends(require_zanzibar_permission("control", resource_type="session"))],
)
async def start_session_proxy(session_id: str, request: Request) -> Any:
    """Move a lobby to active (requires 'control'; game_session).

    The gateway then tells its WebSocket clients that the session started. The owner's reply
    supplies the status. The gateway keeps no state.
    """
    state = await forward_json(
        request, service=SERVICE, method="POST", path=f"{SESSIONS}/{session_id}/start"
    )
    await ws_manager.broadcast(
        session_id, {"type": "session_started", "sessionId": session_id, "status": state["status"]}
    )
    return state


@router.post(
    "/api/v1/sessions/{session_id}/hot-swap",
    dependencies=[Depends(require_zanzibar_permission("observe", resource_type="session"))],
)
async def hot_swap_session_proxy(session_id: str, req: HotSwapRequest, request: Request) -> Any:
    """Hand turn control from an AI stand-in to a player (game_session, which releases the stand-in)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="POST",
        path=f"{SESSIONS}/{session_id}/hot-swap",
        json_body={"character_id": str(req.character_id)},
    )


@router.post(
    "/api/v1/sessions/{session_id}/turns/advance",
    dependencies=[Depends(require_zanzibar_permission("control", resource_type="session"))],
)
async def advance_turn_proxy(session_id: str, request: Request) -> Any:
    """Advance the session to its next turn (requires 'control'; game_session)."""
    return await forward_json(
        request, service=SERVICE, method="POST", path=f"{SESSIONS}/{session_id}/next-turn"
    )


@router.post(
    "/api/v1/sessions/{session_id}/dm-override",
    dependencies=[Depends(require_zanzibar_permission("control", resource_type="session"))],
)
async def dm_override_proxy(session_id: str, req: DMOverrideRequest, request: Request) -> Any:
    """Record a DM override on the session (requires 'control'; game_session)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="POST",
        path=f"{SESSIONS}/{session_id}/dm-override",
        json_body=req.model_dump(mode="json"),
    )


@router.post(
    "/api/v1/sessions/{session_id}/atmosphere",
    dependencies=[Depends(require_zanzibar_permission("control", resource_type="session"))],
)
async def update_atmosphere_proxy(
    session_id: str, req: AtmosphereUpdateRequest, request: Request
) -> Any:
    """Change the location, lighting, and mood (requires 'control'; game_session)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="POST",
        path=f"{SESSIONS}/{session_id}/atmosphere",
        json_body=req.model_dump(mode="json"),
    )


@router.get(
    "/api/v1/sessions/{session_id}/events",
    dependencies=[Depends(require_zanzibar_permission("observe", resource_type="session"))],
)
async def list_session_events_proxy(session_id: str, request: Request) -> Any:
    """Read the session chronicle feed in commit order (requires 'observe'; game_session)."""
    return await forward_json(
        request, service=SERVICE, method="GET", path=f"{SESSIONS}/{session_id}/events"
    )


@router.get(
    "/api/v1/sessions/{session_id}/absentee-recap",
    dependencies=[Depends(require_zanzibar_permission("observe", resource_type="session"))],
)
async def get_absentee_recap_proxy(session_id: str, request: Request) -> Any:
    """Read the stand-in turns and penalties of the session (requires 'observe'; game_session)."""
    return await forward_json(
        request, service=SERVICE, method="GET", path=f"{SESSIONS}/{session_id}/absentee-recap"
    )
