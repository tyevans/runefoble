"""Wire models for the OBS party vitals overlay and its live socket frames."""

from __future__ import annotations

from gateway_api.audience_replies import (
    BoardAudienceReply,
    CameraTarget,
    SessionAudienceReply,
    SpectatorPartyMember,
)
from pydantic import BaseModel, Field


class PartyVitalsData(BaseModel):
    """Party vitals and camera target for the overlay. Built only from owner views."""

    session_id: str
    party: list[SpectatorPartyMember] = Field(default_factory=list)
    camera: CameraTarget
    round: int
    position: str = "bottom"
    transparent: bool = True


class RollAnimationMessage(BaseModel):
    """A dice roll that the overlay animates. It holds no state and no owner read."""

    type: str = "roll_animation"
    roller_name: str
    dice_formula: str
    result: int
    is_critical: bool
    is_fumble: bool


def compose_party_vitals(
    session: SessionAudienceReply,
    board: BoardAudienceReply,
    position: str = "bottom",
) -> PartyVitalsData:
    """Join the owner views into the overlay payload."""
    return PartyVitalsData(
        session_id=session.session_id,
        party=board.party,
        camera=board.camera,
        round=session.round,
        position=position,
    )


__all__ = ["PartyVitalsData", "RollAnimationMessage", "compose_party_vitals"]
