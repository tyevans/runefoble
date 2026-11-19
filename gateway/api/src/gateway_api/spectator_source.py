"""Reads and writes the audience state through the owning services (ADR-0015 b).

The gateway holds no session state. `game_session` builds the session view. `board_state` builds
the board view, drops the monsters, and holds the camera target. Each owner verifies the caller's
bearer token and checks its own permission. A 4xx answer from an owner passes on through
`UpstreamRejectedError`. A 5xx answer, an unreachable owner, or a reply that does not match the
wire model raises an upstream fault. The gateway never substitutes a value.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from gateway_api.audience_replies import (
    BoardAudienceReply,
    CameraTarget,
    SessionAudienceReply,
)
from gateway_api.upstream_errors import UpstreamRejectedError
from gateway_api.upstreams import UpstreamRegistry
from pydantic import BaseModel
from runefoble_platform.service_client import path

GAME_SESSION = "game_session"
BOARD_STATE = "board_state"
READ_TIMEOUT_S = 5.0
UPSTREAM_INVALID_DETAIL = "Upstream service returned an invalid response"


async def read_audience_views(
    upstreams: UpstreamRegistry, session_id: str, authorization: str | None
) -> tuple[SessionAudienceReply, BoardAudienceReply]:
    """Return the session view and the board view. Both owners check `session.observe` or `board.view`."""
    try:
        session_path = path("api", "v1", "sessions", session_id, "spectator")
        board_path = path("api", "v1", "boards", session_id, "spectator")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        ) from exc
    session = await _call(
        upstreams, GAME_SESSION, "GET", session_path, authorization, SessionAudienceReply
    )
    board = await _call(
        upstreams, BOARD_STATE, "GET", board_path, authorization, BoardAudienceReply
    )
    return session, board


async def focus_camera_on_turn(
    upstreams: UpstreamRegistry,
    session_id: str,
    authorization: str | None,
    body: dict[str, Any],
) -> CameraTarget:
    """Ask the board owner to center the camera on the active token. Return the owner's target."""
    return await _focus_camera(upstreams, session_id, authorization, "turn-started", body)


async def focus_camera_on_move(
    upstreams: UpstreamRegistry,
    session_id: str,
    authorization: str | None,
    body: dict[str, Any],
) -> CameraTarget:
    """Ask the board owner to center the camera on a move destination. Return the owner's target."""
    return await _focus_camera(upstreams, session_id, authorization, "token-moved", body)


async def _focus_camera(
    upstreams: UpstreamRegistry,
    session_id: str,
    authorization: str | None,
    focus: str,
    body: dict[str, Any],
) -> CameraTarget:
    try:
        focus_path = path("api", "v1", "boards", session_id, "camera", focus)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        ) from exc
    return await _call(
        upstreams, BOARD_STATE, "POST", focus_path, authorization, CameraTarget, json=body
    )


async def _call[Reply: BaseModel](
    upstreams: UpstreamRegistry,
    service: str,
    method: str,
    request_path: str,
    authorization: str | None,
    reply_model: type[Reply],
    *,
    json: dict[str, Any] | None = None,
) -> Reply:
    reply = await upstreams.client(service).send(
        method,
        request_path,
        authorization=authorization,
        timeout_s=READ_TIMEOUT_S,
        json=json,
    )
    if reply.status_code >= 400:
        raise UpstreamRejectedError(service, reply)
    try:
        return reply_model.model_validate_json(reply.body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=UPSTREAM_INVALID_DETAIL
        ) from exc


__all__ = ["focus_camera_on_move", "focus_camera_on_turn", "read_audience_views"]
