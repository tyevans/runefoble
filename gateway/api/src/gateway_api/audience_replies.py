"""Wire models for the audience replies that the owning services send.

The owners build the views and remove the private fields (ADR-0015 b). The gateway validates
each reply against these models and copies the fields. A reply that does not match is an
upstream fault and maps to 502. The gateway never fills in a default for a missing owner field.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

DEFAULT_EASING = "cubic-bezier(0.25, 0.1, 0.25, 1.0)"


class SpectatorToken(BaseModel):
    """A token the audience may see. Monsters never reach the gateway."""

    id: str
    name: str
    x: int
    y: int
    token_type: str


class SpectatorPartyMember(BaseModel):
    """A player character with hit points."""

    id: str
    name: str
    hp: int
    max_hp: int


class SpectatorAtmosphere(BaseModel):
    """Public scene atmosphere."""

    location_name: str = "Unknown Location"
    lighting: str = "Normal"
    mood: str = "Neutral"
    description: str = ""
    ambient_audio_prompt: str | None = None


class SpectatorChronicleMessage(BaseModel):
    """One public chronicle line."""

    id: str
    speaker: str
    text: str
    timestamp: str
    action_type: str = "speech"


class CameraTarget(BaseModel):
    """The camera target that the board owner holds for a session."""

    target_x: float
    target_y: float
    zoom: float
    duration_ms: int
    easing: str = DEFAULT_EASING
    active_token_id: str | None = None
    active_character_id: str | None = None
    reason: str
    timestamp: str = ""


class SessionAudienceReply(BaseModel):
    """The session view from `game_session`."""

    session_id: str
    status: str
    round: int
    atmosphere: SpectatorAtmosphere | None = None
    chronicle: list[SpectatorChronicleMessage] = Field(default_factory=list)


class BoardAudienceReply(BaseModel):
    """The board view from `board_state`, with the camera target."""

    session_id: str
    cols: int
    rows: int
    tokens: list[SpectatorToken] = Field(default_factory=list)
    party: list[SpectatorPartyMember] = Field(default_factory=list)
    camera: CameraTarget


__all__ = [
    "DEFAULT_EASING",
    "BoardAudienceReply",
    "CameraTarget",
    "SessionAudienceReply",
    "SpectatorAtmosphere",
    "SpectatorChronicleMessage",
    "SpectatorPartyMember",
    "SpectatorToken",
]
