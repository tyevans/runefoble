"""Voice Room HTTP API routes for status querying and DM moderation."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel
from voice_agent.room import get_voice_room_coordinator

logger = logging.getLogger("runefoble.voice_agent.room_routes")

router = APIRouter(prefix="/api/v1/voice/rooms", tags=["Voice Rooms"])


class KickPeerRequest(BaseModel):
    peer_id: str
    reason: str = "kicked_by_dm"


def extract_user_id(
    request: Request,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    authorization: str | None = Header(None, alias="Authorization"),
) -> str:
    """Extract authenticated subject identifier from header, bearer token, or query."""
    if x_user_id:
        return x_user_id
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:].strip()
    param_user = request.query_params.get("user_id") or request.query_params.get("token")
    if param_user:
        return param_user
    return "guest_user"


@router.get("/{session_id}")
async def get_voice_room(session_id: str):
    """Retrieve active room participants, roles, mute states, and audio telemetry."""
    coord = get_voice_room_coordinator()
    return await coord.get_room_summary(session_id)


@router.post("/{session_id}/kick")
async def kick_voice_peer(
    session_id: str,
    req: KickPeerRequest,
    request: Request,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    authorization: str | None = Header(None, alias="Authorization"),
):
    """DM moderation endpoint: kick peer from active voice room (Zanzibar enforced)."""
    user_id = extract_user_id(request, x_user_id, authorization)
    coord = get_voice_room_coordinator()

    # Enforce SpiceDB Zanzibar authorization (Hard Invariant 1)
    spicedb = coord.spicedb
    is_allowed = (
        await spicedb.check_permission("game_session", session_id, "control", "user", user_id)
        or await spicedb.check_permission("session", session_id, "control", "user", user_id)
        or await spicedb.check_permission("campaign", session_id, "run_session", "user", user_id)
        or await spicedb.check_permission("campaign", session_id, "manage", "user", user_id)
        or await spicedb.check_permission("campaign", session_id, "owner", "user", user_id)
        or await spicedb.check_permission("campaign", session_id, "dungeon_master", "user", user_id)
    )

    if not is_allowed:
        logger.warning(
            "DM kick rejected: subject '%s' lacks DM control permissions on session '%s'",
            user_id,
            session_id,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "permission_denied",
                "message": f"Subject 'user:{user_id}' lacks DM moderation permissions on session '{session_id}'.",
                "required_permission": "control",
                "resource": f"session:{session_id}",
                "subject": f"user:{user_id}",
            },
        )

    return await coord.kick_peer(
        session_id=session_id,
        peer_id=req.peer_id,
        kicked_by=user_id,
        reason=req.reason,
    )
