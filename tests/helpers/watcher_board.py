"""Frontdoor setup of a board for The Watcher move-proposal tests (TASK-0814).

The Watcher proposes a move to a live `board_state`. These helpers create the board and its
tokens through the public `board_state` routes, and read a token position from the public
board read. No test writes board state directly.
"""

from __future__ import annotations

from typing import Any

import httpx

from tests.realtime_session import bearer


def open_board_with_tokens(
    board_url: str,
    session_id: str,
    campaign_id: str,
    *,
    owner: str,
    cols: int,
    rows: int,
    tokens: list[dict[str, Any]],
) -> None:
    """Create the session board, then place each token through `POST .../tokens`."""
    created = httpx.post(
        f"{board_url}/api/v1/boards",
        json={"campaign_id": campaign_id, "session_id": session_id, "cols": cols, "rows": rows},
        headers=bearer(owner),
    )
    assert created.status_code == 200, created.text
    for token in tokens:
        placed = httpx.post(
            f"{board_url}/api/v1/boards/{session_id}/tokens",
            json={**token, "is_friendly": True},
            headers=bearer(owner),
        )
        assert placed.status_code == 200, placed.text


def token_position(board_url: str, session_id: str, token_id: str, owner: str) -> tuple[int, int]:
    """Return the token's (x, y) from the public board read."""
    board = httpx.get(f"{board_url}/api/v1/boards/{session_id}", headers=bearer(owner))
    assert board.status_code == 200, board.text
    token = board.json()["tokens"][token_id]
    return token["x"], token["y"]
