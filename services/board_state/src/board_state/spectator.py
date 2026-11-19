"""Audience-safe board projection. The board owner drops monsters before any gateway sees data.

Monsters keep their stat blocks and hidden state on the owner side only. The projection copies
an allowlist of fields, so a field added to the token model stays off the audience view until
it is listed here.
"""

from __future__ import annotations

from typing import Literal

from board_state.camera.models import CameraTarget
from board_state.models import BoardState
from pydantic import BaseModel, Field


class SpectatorToken(BaseModel):
    """A token that the audience may see."""

    id: str
    name: str
    x: int
    y: int
    token_type: Literal["pc", "npc", "obstacle"]


class SpectatorPartyMember(BaseModel):
    """A player character with hit points. The overlay HUD draws these."""

    id: str
    name: str
    hp: int
    max_hp: int


class SpectatorBoardView(BaseModel):
    """The board as the audience may see it, with the current camera target."""

    session_id: str
    cols: int
    rows: int
    tokens: list[SpectatorToken] = Field(default_factory=list)
    party: list[SpectatorPartyMember] = Field(default_factory=list)
    camera: CameraTarget = Field(default_factory=CameraTarget.initial)


def project_spectator_board(state: BoardState) -> SpectatorBoardView:
    """Return the audience view of one board. Monsters never appear in the result."""
    visible = [tok for tok in state.tokens.values() if tok.token_type != "monster"]
    return SpectatorBoardView(
        session_id=state.session_id,
        cols=state.cols,
        rows=state.rows,
        tokens=[
            SpectatorToken(
                id=tok.token_id,
                name=tok.name,
                x=tok.x,
                y=tok.y,
                token_type=tok.token_type,
            )
            for tok in visible
        ],
        party=[
            SpectatorPartyMember(id=tok.token_id, name=tok.name, hp=tok.hp, max_hp=tok.hp)
            for tok in visible
            if tok.token_type == "pc" and tok.hp is not None
        ],
        camera=state.camera,
    )
