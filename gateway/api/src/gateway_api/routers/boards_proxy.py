"""Board and token routes proxied to board_state, which owns the grid and the tokens (TASK-0582).

The DM battlemap set-up flow creates the board and places the party tokens here (TASK-0922).
The create route is hand-written: after board_state answers 2xx, it sends `board_ready` to the
session room. It is the only source of that frame. A client frame of that kind is refused.

The gateway verifies the bearer token, then forwards the request with that same token.
board_state checks every board and token permission (ADR-0001, ADR-0015). The gateway keeps
no board state and returns no substitute body. A failed upstream call returns the mapping in
`upstream_errors.py`: 503 when unreachable, 502 on upstream 5xx, upstream 4xx unchanged.

Each route is a row in `ROUTES` (TASK-0822).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from gateway_api.auth import get_principal
from gateway_api.dependencies import ws_manager
from gateway_api.models import BoardCreateRequest, TokenMoveRequest, TokenPlaceRequest
from gateway_api.proxy import forward_json
from gateway_api.proxy_table import ProxyRoute, register_proxy_routes
from runefoble_platform.service_client import owner_routes

SERVICE = "board_state"

router = APIRouter(tags=["Boards & Tokens"])

ROUTES = (
    ProxyRoute(
        "GET",
        "/api/v1/boards/{session_id}",
        (),
        SERVICE,
        name="get_board",
        doc="Read the board of a session (board_state).",
        owner=owner_routes.get_board,
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/boards/{session_id}/tokens/{token_id}",
        (),
        SERVICE,
        name="get_token",
        doc="Read one placed token of a session's board (board_state).",
        owner=owner_routes.get_token,
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/boards/{session_id}/tokens",
        (),
        SERVICE,
        name="place_token",
        doc="Place a token on the board (board_state checks the board and character permissions).",
        owner=owner_routes.place_token,
        body="json",
        body_model=TokenPlaceRequest,
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/boards/{session_id}/tokens/{token_id}/move",
        (),
        SERVICE,
        name="move_token",
        doc="Move a token on the board (board_state checks `board_token.move`).",
        owner=owner_routes.move_token,
        body="json",
        body_model=TokenMoveRequest,
        principal=True,
    ),
)

register_proxy_routes(router, ROUTES)


@router.post("/api/v1/boards", dependencies=[Depends(get_principal)])
async def create_board_proxy(req: BoardCreateRequest, request: Request) -> Any:
    """Create the board of a session (board_state checks `campaign.run_session`).

    After the owner answers 2xx, the gateway tells the session sockets that the board exists.
    A refused or failed create raises before the broadcast, so no frame goes out.
    """
    route = owner_routes.create_board()
    board = await forward_json(
        request,
        service=SERVICE,
        method=route.method,
        path=route.path,
        json_body=req.model_dump(mode="json"),
    )
    await ws_manager.broadcast(req.session_id, {"type": "board_ready", "sessionId": req.session_id})
    return board
