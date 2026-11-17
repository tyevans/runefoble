"""HTTP client for voice_agent speech conditioning (TASK-0675, ADR-0007).

game_session never imports the voice_agent package. It calls the public route
POST /api/v1/voice/dsp/condition. Upstream failures raise VoiceAgentUnavailableError.
Callers must surface the error. They must not substitute a value.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

VOICE_AGENT_URL_ENV = "RUNEFOBLE_VOICE_AGENT_URL"
VOICE_AGENT_TIMEOUT_ENV = "RUNEFOBLE_VOICE_AGENT_TIMEOUT_SECONDS"
DEFAULT_TIMEOUT_SECONDS = 5.0
CONDITION_PATH = "/api/v1/voice/dsp/condition"


class VoiceAgentUnavailableError(Exception):
    """voice_agent did not return a usable speech conditioning result."""


class VoiceDSPResult(BaseModel):
    original_text: str
    conditioned_text: str
    active_filters: list[str] = Field(default_factory=list)
    dsp_config: dict[str, Any] = Field(default_factory=dict)


def _base_url() -> str:
    url = os.environ.get(VOICE_AGENT_URL_ENV, "").strip()
    if not url:
        raise VoiceAgentUnavailableError(f"{VOICE_AGENT_URL_ENV} is not configured")
    return url.rstrip("/")


def _timeout_seconds() -> float:
    raw = os.environ.get(VOICE_AGENT_TIMEOUT_ENV)
    return float(raw) if raw else DEFAULT_TIMEOUT_SECONDS


async def condition_speech_text(
    text: str, filters: list[str], authorization: str | None
) -> dict[str, Any]:
    """Ask voice_agent to condition speech text for the given affliction filters.

    The caller's `Authorization` value is forwarded unchanged. voice_agent verifies
    the bearer token itself (ADR-0015 c). No service credential exists yet (ADR-0015 e).
    With no caller token, voice_agent refuses the call and this raises.
    """
    url = f"{_base_url()}{CONDITION_PATH}"
    headers = {"Authorization": authorization} if authorization else {}
    try:
        async with httpx.AsyncClient(timeout=_timeout_seconds()) as client:
            response = await client.post(
                url, json={"text": text, "filters": filters}, headers=headers
            )
    except httpx.HTTPError as exc:
        raise VoiceAgentUnavailableError(f"voice_agent is unreachable: {exc}") from exc

    if response.status_code != 200:
        raise VoiceAgentUnavailableError(
            f"voice_agent returned HTTP {response.status_code} for speech conditioning"
        )
    try:
        return VoiceDSPResult.model_validate(response.json()).model_dump()
    except (ValueError, ValidationError) as exc:
        raise VoiceAgentUnavailableError("voice_agent returned an invalid DSP result") from exc


__all__ = [
    "CONDITION_PATH",
    "VOICE_AGENT_URL_ENV",
    "VoiceAgentUnavailableError",
    "condition_speech_text",
]
