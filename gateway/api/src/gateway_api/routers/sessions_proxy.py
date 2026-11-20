"""Tabletop session routes proxied to game_session, which owns session state (TASK-0581).

The gateway keeps the public paths and verifies the caller's bearer token on each route. It
forwards that token, so game_session verifies the caller again and checks the permission that
the route needs. The gateway stores no session state. A failed upstream call returns the mapping
in `upstream_errors.py`: 503 when unreachable, 502 on upstream 5xx, upstream 4xx unchanged.

`hot-swap` keeps a gateway check because game_session does not check the same permission for
the same caller: it needs `observe` here, and the owner checks `participate` and
`character.edit`. `dm-override` and `atmosphere` have no gateway check: game_session checks
`session.control`. `join` has no gateway check: game_session checks `participate` and seats
the verified caller (TASK-0889). `end` has no gateway check: game_session checks `session.control`
and refuses an end from any status but `active`. `events` and `absentee-recap` keep their
gateway check because game_session answers 404 for an unknown session before it checks
`observe`. Without the gateway check, a caller could tell a session that exists from one that
does not.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from gateway_api.auth import get_principal, require_zanzibar_permission
from gateway_api.dependencies import ws_manager
from gateway_api.models import AtmosphereUpdateRequest, DMOverrideRequest, JoinSessionRequest
from gateway_api.proxy import UPSTREAM_INVALID_DETAIL, forward_bytes, forward_json, owner_route
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from runefoble_platform.service_client import owner_routes

logger = logging.getLogger("runefoble.gateway.sessions_proxy")

SERVICE = "game_session"
SESSIONS = "/api/v1/sessions"

router = APIRouter(tags=["Tabletop & Game Sessions"])

_VERIFIED = [Depends(get_principal)]


class SessionStatusReply(BaseModel):
    """The part of the owner's start or end reply that the gateway reads. Other fields pass through."""

    model_config = ConfigDict(extra="allow")

    status: str


class HotSwapRequest(BaseModel):
    character_id: UUID = Field(alias="characterId")

    model_config = ConfigDict(populate_by_name=True)


@router.get("/api/v1/sessions/{session_id}", dependencies=_VERIFIED)
async def get_session_proxy(session_id: str, request: Request) -> Any:
    """Read session state, participants, and turn index (requires 'observe'; game_session)."""
    route = owner_route(owner_routes.get_session, session_id)
    return await forward_json(request, service=SERVICE, method=route.method, path=route.path)


@router.post("/api/v1/sessions/{session_id}/join", dependencies=_VERIFIED)
async def join_session_proxy(session_id: str, req: JoinSessionRequest, request: Request) -> Any:
    """Seat the verified caller in the lobby with one character (game_session checks 'participate')."""
    route = owner_route(owner_routes.join_session, session_id)
    return await forward_json(
        request,
        service=SERVICE,
        method=route.method,
        path=route.path,
        json_body=req.model_dump(mode="json"),
    )


@router.post("/api/v1/sessions/{session_id}/roll", dependencies=_VERIFIED)
async def roll_dice_proxy(session_id: str, request: Request) -> Any:
    """Evaluate a dice roll for the verified caller (game_session checks 'participate').

    The body goes to the owner unchanged. The owner's reply is the stored roll. The gateway
    keeps no state. The live `dice_rolled` frame comes from the owner's `DiceRolled` event.
    """
    route = owner_route(owner_routes.roll_session, session_id)
    return await forward_bytes(request, service=SERVICE, method=route.method, path=route.path)


@router.post("/api/v1/sessions/{session_id}/start", dependencies=_VERIFIED)
async def start_session_proxy(session_id: str, request: Request) -> Any:
    """Move a lobby to active (game_session checks 'control').

    The gateway then tells its WebSocket clients that the session started. This route is the
    only source of the `session_started` frame (TASK-0910). The owner's reply supplies the
    status. A reply without a status is an upstream contract error and returns 502. The gateway
    keeps no state.
    """
    state = await forward_json(
        request, service=SERVICE, method="POST", path=f"{SESSIONS}/{session_id}/start"
    )
    reply = _status_reply(state, session_id, "start")
    await ws_manager.broadcast(
        session_id, {"type": "session_started", "sessionId": session_id, "status": reply.status}
    )
    return state


@router.post("/api/v1/sessions/{session_id}/end", dependencies=_VERIFIED)
async def end_session_proxy(session_id: str, request: Request) -> Any:
    """End an active session (game_session checks 'control' and refuses any other status).

    The gateway then tells its WebSocket clients that the session ended. This route is the only
    source of the `session_ended` frame. The owner's reply supplies the status, and a reply
    without a status returns 502. The gateway keeps no state.
    """
    route = owner_route(owner_routes.end_session, session_id)
    state = await forward_json(request, service=SERVICE, method=route.method, path=route.path)
    reply = _status_reply(state, session_id, "end")
    await ws_manager.broadcast(
        session_id, {"type": "session_ended", "sessionId": session_id, "status": reply.status}
    )
    return state


def _status_reply(state: Any, session_id: str, action: str) -> SessionStatusReply:
    """Read the owner's status from a start or end reply. A reply without a status is a 502."""
    try:
        return SessionStatusReply.model_validate(state)
    except ValidationError as exc:
        logger.warning(
            "Upstream %s %s reply has no status: session %s", SERVICE, action, session_id
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=UPSTREAM_INVALID_DETAIL
        ) from exc


@router.post(
    "/api/v1/sessions/{session_id}/hot-swap",
    dependencies=[Depends(require_zanzibar_permission("observe", resource_type="game_session"))],
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


@router.post("/api/v1/sessions/{session_id}/turns/advance", dependencies=_VERIFIED)
async def advance_turn_proxy(session_id: str, request: Request) -> Any:
    """Advance the session to its next turn (game_session checks 'control')."""
    return await forward_json(
        request, service=SERVICE, method="POST", path=f"{SESSIONS}/{session_id}/next-turn"
    )


@router.post(
    "/api/v1/sessions/{session_id}/dm-override",
)
async def dm_override_proxy(session_id: str, req: DMOverrideRequest, request: Request) -> Any:
    """Record a DM override on the session (game_session checks 'control')."""
    return await forward_json(
        request,
        service=SERVICE,
        method="POST",
        path=f"{SESSIONS}/{session_id}/dm-override",
        json_body=req.model_dump(mode="json"),
    )


@router.post(
    "/api/v1/sessions/{session_id}/atmosphere",
)
async def update_atmosphere_proxy(
    session_id: str, req: AtmosphereUpdateRequest, request: Request
) -> Any:
    """Change the location, lighting, and mood (game_session checks 'control')."""
    return await forward_json(
        request,
        service=SERVICE,
        method="POST",
        path=f"{SESSIONS}/{session_id}/atmosphere",
        json_body=req.model_dump(mode="json"),
    )


@router.get(
    "/api/v1/sessions/{session_id}/events",
    dependencies=[Depends(require_zanzibar_permission("observe", resource_type="game_session"))],
)
async def list_session_events_proxy(session_id: str, request: Request) -> Any:
    """Read the session chronicle feed in commit order (requires 'observe'; game_session)."""
    return await forward_json(
        request, service=SERVICE, method="GET", path=f"{SESSIONS}/{session_id}/events"
    )


@router.get(
    "/api/v1/sessions/{session_id}/absentee-recap",
    dependencies=[Depends(require_zanzibar_permission("observe", resource_type="game_session"))],
)
async def get_absentee_recap_proxy(session_id: str, request: Request) -> Any:
    """Read the stand-in turns and penalties of the session (requires 'observe'; game_session)."""
    return await forward_json(
        request, service=SERVICE, method="GET", path=f"{SESSIONS}/{session_id}/absentee-recap"
    )
