"""HTTP client for character_sheet stand-in activation, release, and policy reads.

game_session never imports the character_sheet package. It calls public routes only.
Activation and release call POST /api/v1/characters/{character_id}/stand-in with the verified
bearer of the player whose session action triggers it (ADR-0015 c). The policy read calls
GET /api/v1/characters/{character_id}/guardrails with the service credential, because the
session owner who starts an auto-pilot turn does not hold a grant on the absent character
(ADR-0015 e). Upstream failures raise CharacterSheetUnavailableError. Callers must surface the
error. They must not substitute a value (ADR-0015 b).
"""

from __future__ import annotations

import os
from uuid import UUID

import httpx
from runefoble_platform.service_client import ServiceClient, UpstreamError
from runefoble_platform.service_credential import expected_service_credential
from runefoble_platform.stand_in_guardrails import StandInGuardrailPolicy

CHARACTER_SHEET_URL_ENV = "RUNEFOBLE_CHARACTER_SHEET_URL"
CHARACTER_SHEET_TIMEOUT_SECONDS = 5.0
STAND_IN_PATH = "/api/v1/characters/{character_id}/stand-in"
GUARDRAILS_PATH = "/api/v1/characters/{character_id}/guardrails"


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


async def fetch_stand_in_policy(character_id: UUID) -> StandInGuardrailPolicy:
    """Read the stand-in policy stored on the character. Raise CharacterSheetUnavailableError.

    The stored policy is the only policy an auto-pilot turn may use. A missing or invalid answer
    is an error. No default policy takes its place.
    """
    client = ServiceClient("character_sheet", _base_url(), expected_service_credential())
    try:
        reply = await client.send(
            "GET",
            GUARDRAILS_PATH.format(character_id=character_id),
            authorization=None,
            timeout_s=CHARACTER_SHEET_TIMEOUT_SECONDS,
        )
    except UpstreamError as exc:
        raise CharacterSheetUnavailableError(str(exc)) from exc
    finally:
        await client.aclose()

    if reply.status_code != 200:
        raise CharacterSheetUnavailableError(
            f"character_sheet returned HTTP {reply.status_code} for the stored stand-in policy"
        )
    try:
        return StandInGuardrailPolicy.model_validate_json(reply.body)
    except ValueError as exc:
        raise CharacterSheetUnavailableError(
            "character_sheet returned an invalid stand-in policy"
        ) from exc


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
    "fetch_stand_in_policy",
    "release_stand_in",
]
