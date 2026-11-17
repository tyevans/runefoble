"""Read client for the board state service. Reads the visible tokens of a session board."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException
from the_watcher.dependencies import logger

TOKEN_FIELDS = ("token_id", "name", "token_type", "x", "y", "hp", "is_friendly")


async def fetch_visible_tokens(base_url: str | None, session_id: str) -> list[dict[str, Any]]:
    """Return the tokens on the session board. A session with no board has no tokens.

    Any other failure, or a missing board state URL, is raised as HTTP 503.
    """
    unavailable = HTTPException(
        status_code=503,
        detail={"error": "backend_unavailable", "backend": "board_state"},
    )
    if not base_url:
        logger.error("RUNEFOBLE_BOARD_STATE_URL is not set. Cannot read board tokens.")
        raise unavailable

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{base_url}/api/v1/boards/{session_id}")
    except httpx.HTTPError as e:
        logger.error("Board state service unreachable at %s: %s", base_url, e)
        raise unavailable from e

    if res.status_code == 404:
        return []
    if res.status_code != 200:
        logger.error("Board state service returned HTTP %s", res.status_code)
        raise unavailable

    tokens: dict[str, Any] = res.json().get("tokens", {})
    return [{field: token.get(field) for field in TOKEN_FIELDS} for token in tokens.values()]
