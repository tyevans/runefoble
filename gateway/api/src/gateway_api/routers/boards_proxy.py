"""Board and token routes proxied to board_state, which owns the grid and the tokens (TASK-0582).

The gateway verifies the bearer token, then forwards the request with that same token.
board_state checks every board and token permission (ADR-0001, ADR-0015). The gateway keeps
no board state and returns no substitute body. A failed upstream call returns the mapping in
`upstream_errors.py`: 503 when unreachable, 502 on upstream 5xx, upstream 4xx unchanged.

Each route is a row in `ROUTES` (TASK-0822).
"""

from __future__ import annotations

from fastapi import APIRouter
from gateway_api.models import TokenMoveRequest
from gateway_api.proxy_table import ProxyRoute, register_proxy_routes
from runefoble_platform.service_client import owner_routes

SERVICE = "board_state"

router = APIRouter(tags=["Boards & Tokens"])

ROUTES = (
    ProxyRoute(
        "GET",
        "/api/v1/boards/{session_id}",
        ("api", "v1", "boards", "{session_id}"),
        SERVICE,
        name="get_board",
        doc="Read the board of a session (board_state).",
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
