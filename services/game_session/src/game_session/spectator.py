"""Audience-safe session projection. The session owner builds it from its own state.

The projection copies an allowlist of fields. It carries the session status, the combat round,
the scene atmosphere, and the public chronicle feed. DM notes and the other owner-only fields
stay out of the result.
"""

from __future__ import annotations

from uuid import UUID

from game_session.chronicle import ChronicleEntry
from game_session.models.session import GameSessionState
from pydantic import BaseModel, Field


class SpectatorAtmosphere(BaseModel):
    """Public scene atmosphere. Each field falls back to a neutral default when the DM omits it."""

    location_name: str = "Unknown Location"
    lighting: str = "Normal"
    mood: str = "Neutral"
    description: str = ""
    ambient_audio_prompt: str | None = None


class SpectatorChronicleLine(BaseModel):
    """One public chronicle line for the audience."""

    id: str
    speaker: str
    text: str
    timestamp: str
    action_type: str = "speech"


class SpectatorSessionView(BaseModel):
    """The session as the audience may see it."""

    session_id: str
    status: str
    round: int
    atmosphere: SpectatorAtmosphere | None = None
    chronicle: list[SpectatorChronicleLine] = Field(default_factory=list)


def project_spectator_session(
    session_id: UUID, state: GameSessionState, entries: list[ChronicleEntry]
) -> SpectatorSessionView:
    """Return the audience view of one session. `entries` is the chronicle in commit order."""
    return SpectatorSessionView(
        session_id=str(session_id),
        status=state.status,
        round=state.combat_round,
        atmosphere=_atmosphere(state.atmosphere),
        chronicle=[_line(entry) for entry in entries],
    )


def _atmosphere(raw: dict[str, object] | None) -> SpectatorAtmosphere | None:
    if not raw:
        return None
    return SpectatorAtmosphere(
        location_name=str(raw.get("location_name", "Unknown Location")),
        lighting=str(raw.get("lighting", "Normal")),
        mood=str(raw.get("mood", "Neutral")),
        description=str(raw.get("description", "")),
        ambient_audio_prompt=_optional_str(raw.get("ambient_audio_prompt")),
    )


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)


def _line(entry: ChronicleEntry) -> SpectatorChronicleLine:
    return SpectatorChronicleLine(
        id=entry.event_id,
        speaker=entry.speaker,
        text=entry.text,
        timestamp=entry.occurred_at.isoformat(),
        action_type=entry.action_type or "speech",
    )
