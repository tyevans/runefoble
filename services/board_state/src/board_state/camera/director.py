"""Camera focus rules. Each function returns the next camera target from owner data.

The functions hold no state. The board aggregate stores the returned target through a
`CameraFocused` event, so a restart or a new gateway instance reads the same camera.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from board_state.camera.models import (
    DEFAULT_DURATION_MS,
    DEFAULT_EASING,
    DEFAULT_ZOOM,
    CameraTarget,
)

if TYPE_CHECKING:
    from board_state.models import BoardState


class CameraTokenNotFoundError(LookupError):
    """Raised when a focus request names a token that is not on the board. Routers map it to 409."""


def focus_on_turn_started(
    state: BoardState,
    *,
    token_id: str | None,
    character_id: str | None,
    duration_ms: int | None,
    easing: str | None,
) -> CameraTarget:
    """Center the camera on the active token. The request names the token by id or character id."""
    key = token_id or character_id or ""
    token = state.tokens.get(key)
    if token is None:
        raise CameraTokenNotFoundError(f"Token '{key}' is not on the board")
    return CameraTarget(
        target_x=float(token.x),
        target_y=float(token.y),
        zoom=DEFAULT_ZOOM,
        duration_ms=duration_ms if duration_ms is not None else DEFAULT_DURATION_MS,
        easing=easing or DEFAULT_EASING,
        active_token_id=token.token_id,
        active_character_id=character_id or None,
        reason="turn_started",
        timestamp=datetime.now(UTC).isoformat(),
    )


def focus_on_token_moved(
    *,
    token_id: str,
    to_x: int,
    to_y: int,
    duration_ms: int | None,
    easing: str | None,
) -> CameraTarget:
    """Center the camera on the destination of a token move."""
    return CameraTarget(
        target_x=float(to_x),
        target_y=float(to_y),
        zoom=DEFAULT_ZOOM,
        duration_ms=duration_ms if duration_ms is not None else DEFAULT_DURATION_MS,
        easing=easing or DEFAULT_EASING,
        active_token_id=token_id,
        reason="token_moved",
        timestamp=datetime.now(UTC).isoformat(),
    )
