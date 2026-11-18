"""Voice Room HTTP API routes for status querying and DM moderation."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from voice_agent.auth import CallerPrincipal, get_principal
from voice_agent.authz import require_action
from voice_agent.coordinator import get_voice_room_coordinator

logger = logging.getLogger("runefoble.voice_agent.room_routes")

router = APIRouter(
    dependencies=[Depends(get_principal)], prefix="/api/v1/voice/rooms", tags=["Voice Rooms"]
)


class KickPeerRequest(BaseModel):
    peer_id: str
    reason: str = "kicked_by_dm"


@router.get("/{session_id}")
async def get_voice_room(session_id: str):
    """Retrieve active room participants, roles, mute states, and audio telemetry."""
    coord = get_voice_room_coordinator()
    return await coord.get_room_summary(session_id)


@router.post("/{session_id}/kick")
async def kick_voice_peer(
    session_id: str,
    req: KickPeerRequest,
    principal: CallerPrincipal,
):
    """DM moderation endpoint: kick peer from active voice room (Zanzibar enforced)."""
    user_id = principal.user_id
    coord = get_voice_room_coordinator()
    await require_action("session.control", session_id, user_id)
    return await coord.kick_peer(
        session_id=session_id,
        peer_id=req.peer_id,
        kicked_by=user_id,
        reason=req.reason,
    )
