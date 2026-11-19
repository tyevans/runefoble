"""Spectator stream response for the gateway. The owners build the state; this module adds the viewer.

`compose_spectator_state` copies the owner views into the wire shape. It removes nothing and adds
no value. The privacy rules run in `game_session` and `board_state`.
"""

from __future__ import annotations

from gateway_api.audience_replies import (
    BoardAudienceReply,
    SessionAudienceReply,
    SpectatorAtmosphere,
    SpectatorChronicleMessage,
    SpectatorToken,
)
from pydantic import BaseModel, Field


class SpectatorViewerInfo(BaseModel):
    """Connected spectator viewer identity."""

    viewer_id: str
    viewer_name: str


class SpectatorStateResponse(BaseModel):
    """Campaign session state for spectator stream overlays, served from the owners."""

    session_id: str
    status: str
    round: int
    cols: int
    rows: int
    tokens: list[SpectatorToken] = Field(default_factory=list)
    atmosphere: SpectatorAtmosphere | None = None
    chronicle: list[SpectatorChronicleMessage] = Field(default_factory=list)
    viewer: SpectatorViewerInfo | None = None


def compose_spectator_state(
    session: SessionAudienceReply,
    board: BoardAudienceReply,
    viewer: SpectatorViewerInfo,
) -> SpectatorStateResponse:
    """Join the two owner views and add the viewer identity."""
    return SpectatorStateResponse(
        session_id=session.session_id,
        status=session.status,
        round=session.round,
        cols=board.cols,
        rows=board.rows,
        tokens=board.tokens,
        atmosphere=session.atmosphere,
        chronicle=session.chronicle,
        viewer=viewer,
    )
