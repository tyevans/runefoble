"""HTTP client for character_sheet stand-in release (TASK-0570, ADR-0015 (a) and (b)).

game_session never imports the character_sheet package. It calls the public route
POST /api/v1/characters/{character_id}/stand-in. Upstream failures raise
CharacterSheetUnavailableError. Callers must surface the error. They must not substitute a value.
"""

from __future__ import annotations

import os
from uuid import UUID

import httpx

CHARACTER_SHEET_URL_ENV = "RUNEFOBLE_CHARACTER_SHEET_URL"
CHARACTER_SHEET_TIMEOUT_SECONDS = 5.0
STAND_IN_PATH = "/api/v1/characters/{character_id}/stand-in"


class CharacterSheetUnavailableError(Exception):
    """character_sheet did not confirm the stand-in change."""


def _base_url() -> str:
    url = os.environ.get(CHARACTER_SHEET_URL_ENV, "").strip()
    if not url:
        raise CharacterSheetUnavailableError(f"{CHARACTER_SHEET_URL_ENV} is not configured")
    return url.rstrip("/")


async def release_stand_in(character_id: UUID, session_id: UUID) -> None:
    """Release the AI stand-in on a character so the returning player takes control."""
    url = f"{_base_url()}{STAND_IN_PATH.format(character_id=character_id)}"
    try:
        async with httpx.AsyncClient(timeout=CHARACTER_SHEET_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json={"active": False, "session_id": str(session_id)})
    except httpx.HTTPError as exc:
        raise CharacterSheetUnavailableError(f"character_sheet is unreachable: {exc}") from exc

    if response.status_code != 200:
        raise CharacterSheetUnavailableError(
            f"character_sheet returned HTTP {response.status_code} for stand-in release"
        )


__all__ = [
    "CHARACTER_SHEET_URL_ENV",
    "CharacterSheetUnavailableError",
    "release_stand_in",
]
