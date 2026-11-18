"""Reads the spectator and overlay source state from the owning services (ADR-0015 b).

The gateway holds no session state. `game_session` owns the session status, the atmosphere
and the chronicle feed. `board_state` owns the grid and the tokens. Each owner verifies the
caller's bearer token and checks `session.observe` or `board.view` itself. A 4xx answer from
an owner passes on unchanged. A 5xx answer or an unreachable owner raises the upstream error,
and the caller maps it. The gateway never substitutes a value.

Monsters stay off the audience view. The owner keeps their stats and token type. This module
drops them before any projection runs.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException, status
from gateway_api.upstream_errors import UpstreamRejectedError
from gateway_api.upstreams import UpstreamRegistry
from runefoble_platform.service_client import path

GAME_SESSION = "game_session"
BOARD_STATE = "board_state"
READ_TIMEOUT_S = 5.0
UPSTREAM_INVALID_DETAIL = "Upstream service returned an invalid response"


async def read_session_source(
    upstreams: UpstreamRegistry, session_id: str, authorization: str | None
) -> dict[str, Any]:
    """Return the session, board and chronicle state in the shape the projections read.

    Raise UpstreamRejectedError for a 4xx owner answer. Raise an upstream error when an owner
    fails or is unreachable.
    """
    try:
        session_path = path("api", "v1", "sessions", session_id)
        board_path = path("api", "v1", "boards", session_id)
        events_path = path("api", "v1", "sessions", session_id, "events")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        ) from exc

    session = await _read_json(upstreams, GAME_SESSION, session_path, authorization)
    board = await _read_json(upstreams, BOARD_STATE, board_path, authorization)
    events = await _read_json(upstreams, GAME_SESSION, events_path, authorization)
    return source_from_owner_reads(session_id, session, board, events)


def source_from_owner_reads(
    session_id: str,
    session: Mapping[str, Any],
    board: Mapping[str, Any],
    events: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Map the owner answers to the source shape. Copy only the fields the views need."""
    tokens = board.get("tokens") or {}
    return {
        "session_id": session_id,
        "status": session.get("status", "lobby"),
        "round": session.get("combat_round", 1),
        "atmosphere": session.get("atmosphere"),
        "cols": board.get("cols"),
        "rows": board.get("rows"),
        "tokens": [_token(tok) for tok in tokens.values() if tok.get("token_type") != "monster"],
        "chronicle": [_chronicle_line(entry) for entry in events],
    }


def party_tokens(source: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return the player-character tokens that have hit points. These form the party HUD."""
    return [
        tok
        for tok in source.get("tokens", [])
        if tok.get("token_type") == "pc" and tok.get("hp") is not None
    ]


def _token(tok: Mapping[str, Any]) -> dict[str, Any]:
    # The board owner publishes current HP only. Until it publishes a maximum, the overlay
    # draws the current value as the full bar. Tracked as a follow-up in TASK-0809.
    return {
        "id": str(tok["token_id"]),
        "name": str(tok["name"]),
        "x": int(tok["x"]),
        "y": int(tok["y"]),
        "token_type": tok.get("token_type"),
        "hp": tok.get("hp"),
        "max_hp": tok.get("hp"),
    }


def _chronicle_line(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(entry["event_id"]),
        "speaker": str(entry["speaker"]),
        "text": str(entry["text"]),
        "timestamp": str(entry["occurred_at"]),
        "action_type": str(entry.get("action_type") or "speech"),
    }


async def _read_json(
    upstreams: UpstreamRegistry, service: str, request_path: str, authorization: str | None
) -> Any:
    reply = await upstreams.client(service).send(
        "GET", request_path, authorization=authorization, timeout_s=READ_TIMEOUT_S
    )
    if reply.status_code >= 400:
        raise UpstreamRejectedError(service, reply)
    try:
        return json.loads(reply.body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=UPSTREAM_INVALID_DETAIL
        ) from exc


__all__ = ["party_tokens", "read_session_source", "source_from_owner_reads"]
