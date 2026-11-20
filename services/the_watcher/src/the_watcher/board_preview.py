"""Client that proposes a move to board_state as a ghost preview (TASK-0814).

The Watcher proposes. board_state stages the preview on the board socket, and only the
player's `confirm_move` commits it. The call forwards the speaker's own bearer token, so
board_state checks `board.view` for that user (ADR-0015 c). Any failure is raised as HTTP 503
or as the owner's 4xx. A failed proposal is never reported as a staged preview.
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException
from the_watcher.dependencies import logger


def _unavailable() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={"error": "backend_unavailable", "backend": "board_state"},
    )


async def propose_move_preview(
    base_url: str | None,
    authorization: str,
    session_id: str,
    proposal: dict[str, Any],
    *,
    timeout_s: float,
) -> dict[str, Any]:
    """POST the proposal to board_state and return the staged `ghost_preview` message."""
    if not base_url:
        logger.error("RUNEFOBLE_BOARD_STATE_URL is not set. Cannot stage a move preview.")
        raise _unavailable()

    url = f"{base_url}/api/v1/boards/{session_id}/ghost-previews"
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            res = await client.post(url, json=proposal, headers={"Authorization": authorization})
    except httpx.HTTPError as e:
        logger.error("Board state service unreachable at %s: %s", base_url, e)
        raise _unavailable() from e

    if res.status_code >= 500:
        logger.error("Board state service returned HTTP %s for a move preview", res.status_code)
        raise _unavailable()
    if res.status_code != 200:
        raise HTTPException(status_code=res.status_code, detail=res.text)
    staged: dict[str, Any] = res.json()
    return staged
