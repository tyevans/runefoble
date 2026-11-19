"""Board and token routes proxied to board_state, which owns the grid and the tokens (TASK-0582).

The gateway verifies the bearer token, then forwards the request with that same token.
board_state checks every board and token permission (ADR-0001, ADR-0015). The gateway keeps
no board state and returns no substitute body. A failed upstream call returns the mapping in
`upstream_errors.py`: 503 when unreachable, 502 on upstream 5xx, upstream 4xx unchanged.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from gateway_api.auth import CallerPrincipal
from gateway_api.models import TokenMoveRequest
from gateway_api.proxy import forward_json
from runefoble_platform.service_client import owner_routes, path

SERVICE = "board_state"

router = APIRouter(tags=["Boards & Tokens"])


@router.get("/api/v1/boards/{session_id}")
async def get_board(session_id: str, request: Request, user: CallerPrincipal) -> Any:
    """Read the board of a session (board_state)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="GET",
        path=path("api", "v1", "boards", session_id),
    )


@router.get("/api/v1/boards/{session_id}/tokens/{token_id}")
async def get_token(session_id: str, token_id: str, request: Request, user: CallerPrincipal) -> Any:
    """Read one placed token of a session's board (board_state)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="GET",
        path=path("api", "v1", "boards", session_id, "tokens", token_id),
    )


@router.post("/api/v1/boards/{session_id}/tokens/{token_id}/move")
async def move_token(
    session_id: str,
    token_id: str,
    req: TokenMoveRequest,
    request: Request,
    user: CallerPrincipal,
) -> Any:
    """Move a token on the board (board_state checks `board_token.move`)."""
    route = owner_routes.move_token(session_id, token_id)
    return await forward_json(
        request,
        service=SERVICE,
        method=route.method,
        path=route.path,
        json_body=req.model_dump(mode="json"),
    )
