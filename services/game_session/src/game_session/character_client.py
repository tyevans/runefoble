"""HTTP client for character_sheet stand-in activation and release (TASK-0570, TASK-0690).

game_session never imports the character_sheet package. It calls the public route
POST /api/v1/characters/{character_id}/stand-in. The call carries the verified bearer of the
player whose session action triggers it (ADR-0015 c). Upstream failures raise
CharacterSheetUnavailableError. Callers must surface the error. They must not substitute a
value (ADR-0015 b).
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


async def _set_stand_in(
    character_id: UUID, session_id: UUID, *, active: bool, authorization: str
) -> None:
    """Set the AI stand-in flag on a character. Raise CharacterSheetUnavailableError on failure."""
    url = f"{_base_url()}{STAND_IN_PATH.format(character_id=character_id)}"
    try:
        async with httpx.AsyncClient(timeout=CHARACTER_SHEET_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                json={"active": active, "session_id": str(session_id)},
                headers={"Authorization": authorization},
            )
    except httpx.HTTPError as exc:
        raise CharacterSheetUnavailableError(f"character_sheet is unreachable: {exc}") from exc

    if response.status_code != 200:
        action = "activation" if active else "release"
        raise CharacterSheetUnavailableError(
            f"character_sheet returned HTTP {response.status_code} for stand-in {action}"
        )


async def activate_stand_in(character_id: UUID, session_id: UUID, *, authorization: str) -> None:
    """Hand an absent player's character to the AI stand-in (TASK-0690)."""
    await _set_stand_in(character_id, session_id, active=True, authorization=authorization)


async def release_stand_in(character_id: UUID, session_id: UUID, *, authorization: str) -> None:
    """Release the AI stand-in on a character so the returning player takes control."""
    await _set_stand_in(character_id, session_id, active=False, authorization=authorization)


__all__ = [
    "CHARACTER_SHEET_URL_ENV",
    "CharacterSheetUnavailableError",
    "activate_stand_in",
    "release_stand_in",
]
