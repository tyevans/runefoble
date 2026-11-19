"""Gateway proxy for voice room and stream diagnostics routes owned by voice_agent (TASK-0593).

Each route forwards the caller's bearer token to voice_agent. voice_agent verifies the token
and checks the session permission itself (ADR-0015 c, Hard Invariant 1). The gateway keeps
no room state and adds no permission check of its own. Paths match the owner's public paths.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Request
from gateway_api.proxy import forward_json
from runefoble_platform.service_client import path

router = APIRouter(tags=["Voice Rooms"])

VOICE_SERVICE = "voice_agent"


@router.get("/api/v1/voice/rooms/{session_id}")
async def get_voice_room(session_id: str, request: Request) -> Any:
    """Retrieve room participants, roles, mute states, and audio telemetry from the voice service."""
    return await forward_json(
        request,
        service=VOICE_SERVICE,
        method="GET",
        path=path("api", "v1", "voice", "rooms", session_id),
    )


@router.post("/api/v1/voice/rooms/{session_id}/kick")
async def kick_voice_peer(session_id: str, request: Request, body: Annotated[Any, Body()]) -> Any:
    """Forward a DM kick request. voice_agent checks session.control."""
    return await forward_json(
        request,
        service=VOICE_SERVICE,
        method="POST",
        path=path("api", "v1", "voice", "rooms", session_id, "kick"),
        json_body=body,
    )


@router.get("/api/v1/voice/streams/{session_id}/quality")
async def get_stream_quality(session_id: str, request: Request) -> Any:
    """Forward a stream quality query. The optional peer_id query parameter is passed on."""
    return await forward_json(
        request,
        service=VOICE_SERVICE,
        method="GET",
        path=_stream_path(request, session_id),
        params=dict(request.query_params),
    )


@router.post("/api/v1/voice/streams/{session_id}/report")
async def submit_rtcp_report(
    session_id: str, request: Request, body: Annotated[Any, Body()]
) -> Any:
    """Forward an RTCP receiver report. voice_agent evaluates it and adapts the codec."""
    return await forward_json(
        request,
        service=VOICE_SERVICE,
        method="POST",
        path=_stream_path(request, session_id),
        json_body=body,
    )


@router.get("/api/v1/mobile/companion/profiles")
async def get_mobile_profiles(request: Request) -> Any:
    """Forward the companion audio profile list. voice_agent owns the profiles."""
    return await forward_json(
        request,
        service=VOICE_SERVICE,
        method="GET",
        path=path("api", "v1", "mobile", "companion", "profiles"),
    )


@router.post("/api/v1/mobile/companion/{session_id}/whisper")
async def dispatch_whisper(session_id: str, request: Request, body: Annotated[Any, Body()]) -> Any:
    """Forward a secret DM whisper. voice_agent checks session.control."""
    return await forward_json(
        request,
        service=VOICE_SERVICE,
        method="POST",
        path=path("api", "v1", "mobile", "companion", session_id, "whisper"),
        json_body=body,
    )


@router.post("/api/v1/mobile/companion/{session_id}/turn-alert")
async def dispatch_turn_alert(
    session_id: str, request: Request, body: Annotated[Any, Body()]
) -> Any:
    """Forward a combat turn alert. voice_agent checks session.control."""
    return await forward_json(
        request,
        service=VOICE_SERVICE,
        method="POST",
        path=path("api", "v1", "mobile", "companion", session_id, "turn-alert"),
        json_body=body,
    )


def _stream_path(request: Request, session_id: str) -> str:
    """Return the owner path for a stream action. voice_agent serves only `/api/v1/voice/streams`."""
    action = request.url.path.rsplit("/", 1)[-1]
    return path("api", "v1", "voice", "streams", session_id, action)


__all__ = ["router"]
