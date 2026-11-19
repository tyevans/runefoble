"""The DM battlemap set-up: create the session board, then place the party tokens (TASK-0928).

The gateway composes owner calls only. board_state checks `campaign.run_session` for the board
and the token permissions for each token. The gateway keeps no board state.

`board_ready` goes to the session room once, after the last token call. Thus a client that
reads the board after the frame gets the party tokens. A refused or failed create raises before
any frame. A refused or failed token stops the set-up. The board exists then, so the frame still
goes out, and the reply names the token and says `board_created: true`.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from gateway_api.dependencies import ws_manager
from gateway_api.models import BoardCreateRequest, TokenPlaceRequest
from gateway_api.proxy import forward_json
from gateway_api.upstream_errors import UPSTREAM_UNAVAILABLE_DETAIL, UpstreamRejectedError
from runefoble_platform.service_client import (
    UpstreamFailureError,
    UpstreamUnavailableError,
    error_detail,
    owner_routes,
)

SERVICE = "board_state"


def _token_failure(token: TokenPlaceRequest, status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": f"{token.name}: {detail}",
            "token": token.name,
            "board_created": True,
            "upstream": SERVICE,
        },
    )


async def _place(request: Request, session_id: str, token: TokenPlaceRequest) -> Any:
    route = owner_routes.place_token(session_id)
    return await forward_json(
        request,
        service=SERVICE,
        method=route.method,
        path=route.path,
        json_body=token.model_dump(mode="json"),
    )


async def _place_party(
    request: Request, session_id: str, tokens: list[TokenPlaceRequest]
) -> list[Any] | JSONResponse:
    """Place each token in order. The first failed token stops the loop and gives its reply."""
    placed: list[Any] = []
    for token in tokens:
        try:
            placed.append(await _place(request, session_id, token))
        except UpstreamRejectedError as exc:
            return _token_failure(token, exc.reply.status_code, error_detail(exc.reply.body))
        except UpstreamFailureError:
            return _token_failure(token, 502, UPSTREAM_UNAVAILABLE_DETAIL)
        except UpstreamUnavailableError:
            return _token_failure(token, 503, UPSTREAM_UNAVAILABLE_DETAIL)
    return placed


async def set_up_board(request: Request, req: BoardCreateRequest) -> Any:
    """Create the board, place the tokens, then send `board_ready` once."""
    route = owner_routes.create_board()
    board = await forward_json(
        request,
        service=SERVICE,
        method=route.method,
        path=route.path,
        json_body=req.model_dump(mode="json", exclude={"tokens"}),
    )
    try:
        placed = await _place_party(request, req.session_id, req.tokens)
    finally:
        await ws_manager.broadcast(
            req.session_id, {"type": "board_ready", "sessionId": req.session_id}
        )
    if isinstance(placed, JSONResponse):
        return placed
    return {"board": board, "tokens": placed}
