"""Autonomous Cinematic Director Camera for Live Stream & OBS Overlays.

Tracks active character turn events (TurnStarted) and action centers (TokenMoved),
calculating smooth viewport pan/zoom with cubic-bezier easing within 300ms.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from runefoble_events.board import TokenMoved
from runefoble_events.session import TurnStarted

DEFAULT_EASING = "cubic-bezier(0.25, 0.1, 0.25, 1.0)"
DEFAULT_DURATION_MS = 300
DEFAULT_ZOOM = 1.5

_BEZIER_PATTERN = re.compile(
    r"cubic-bezier\(\s*([\d\.\-]+)\s*,\s*([\d\.\-]+)\s*,\s*([\d\.\-]+)\s*,\s*([\d\.\-]+)\s*\)"
)


def parse_cubic_bezier(easing_str: str) -> tuple[float, float, float, float]:
    """Parse cubic-bezier curve parameters from CSS string.

    Defaults to standard ease (0.25, 0.1, 0.25, 1.0) if unparseable.
    """
    if not easing_str:
        return (0.25, 0.1, 0.25, 1.0)
    match = _BEZIER_PATTERN.match(easing_str.strip())
    if not match:
        return (0.25, 0.1, 0.25, 1.0)
    try:
        p1x, p1y, p2x, p2y = (float(v) for v in match.groups())
        return (p1x, p1y, p2x, p2y)
    except (ValueError, TypeError):
        return (0.25, 0.1, 0.25, 1.0)


def evaluate_cubic_bezier(p1x: float, p1y: float, p2x: float, p2y: float, progress: float) -> float:
    """Evaluate 1D cubic-bezier easing at given normalized progress t in [0.0, 1.0].

    Uses Newton-Raphson method to solve x(t) = progress, then returns y(t).
    """
    t = max(0.0, min(1.0, float(progress)))
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0

    # Iterative Newton-Raphson to solve for curve parameter u where Bx(u) = t
    u = t
    for _ in range(8):
        # Bx(u) = 3*(1-u)^2 * u * p1x + 3*(1-u) * u^2 * p2x + u^3
        one_minus_u = 1.0 - u
        x_est = 3.0 * (one_minus_u**2) * u * p1x + 3.0 * one_minus_u * (u**2) * p2x + (u**3)
        dx = (
            3.0 * (one_minus_u**2) * p1x
            + 6.0 * one_minus_u * u * (p2x - p1x)
            + 3.0 * (u**2) * (1.0 - p2x)
        )
        if abs(dx) < 1e-6:
            break
        u = max(0.0, min(1.0, u - (x_est - t) / dx))

    # Evaluate By(u)
    one_minus_u = 1.0 - u
    y = 3.0 * (one_minus_u**2) * u * p1y + 3.0 * one_minus_u * (u**2) * p2y + (u**3)
    return max(0.0, min(1.0, y))


class CameraTarget(BaseModel):
    """Cinematic camera viewport target for OBS stream and spectator clients."""

    target_x: float = Field(default=0.0, description="Centered grid x-coordinate")
    target_y: float = Field(default=0.0, description="Centered grid y-coordinate")
    zoom: float = Field(default=DEFAULT_ZOOM, description="Viewport zoom multiplier")
    duration_ms: int = Field(default=DEFAULT_DURATION_MS, description="Transition duration in ms")
    easing: str = Field(default=DEFAULT_EASING, description="Cubic-bezier easing curve string")
    active_token_id: str | None = Field(default=None, description="Active focused token ID")
    active_character_id: str | None = Field(default=None, description="Active focused character ID")
    reason: str = Field(default="default", description="Trigger reason (turn_started, token_moved)")
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class CinematicDirector:
    """Autonomous camera director tracking active turns and token action centers."""

    def __init__(
        self,
        default_zoom: float = DEFAULT_ZOOM,
        default_duration_ms: int = DEFAULT_DURATION_MS,
        default_easing: str = DEFAULT_EASING,
    ) -> None:
        self.default_zoom = default_zoom
        self.default_duration_ms = default_duration_ms
        self.default_easing = default_easing
        self.current_target = CameraTarget(
            target_x=0.0,
            target_y=0.0,
            zoom=1.0,
            duration_ms=default_duration_ms,
            easing=default_easing,
            reason="init",
        )

    def calculate_center_on_token(
        self,
        x: float,
        y: float,
        token_id: str | None = None,
        character_id: str | None = None,
        zoom: float | None = None,
        duration_ms: int | None = None,
        easing: str | None = None,
        reason: str = "token_focus",
    ) -> CameraTarget:
        """Calculate smooth pan/zoom target centering on token coordinates."""
        target = CameraTarget(
            target_x=float(x),
            target_y=float(y),
            zoom=zoom if zoom is not None else self.default_zoom,
            duration_ms=duration_ms if duration_ms is not None else self.default_duration_ms,
            easing=easing or self.default_easing,
            active_token_id=token_id,
            active_character_id=character_id,
            reason=reason,
        )
        self.current_target = target
        return target

    def handle_turn_started(
        self,
        event: TurnStarted | dict[str, Any],
        tokens: list[dict[str, Any]] | None = None,
        duration_ms: int | None = None,
        easing: str | None = None,
    ) -> CameraTarget:
        """Center camera on the active character/token for their turn."""
        if isinstance(event, dict):
            token_id = str(event.get("token_id") or "")
            char_id = str(event.get("character_id") or "")
        else:
            token_id = str(event.token_id or "")
            char_id = str(event.character_id or "")

        target_x, target_y = 0.0, 0.0
        found = False
        if tokens:
            for tok in tokens:
                t_id = str(tok.get("id") or "")
                c_id = str(tok.get("character_id") or "")
                if (token_id and t_id == token_id) or (
                    char_id and (c_id == char_id or t_id == char_id)
                ):
                    target_x = float(tok.get("x", 0))
                    target_y = float(tok.get("y", 0))
                    found = True
                    break

        if not found and isinstance(event, dict) and "x" in event and "y" in event:
            target_x = float(event["x"])
            target_y = float(event["y"])

        return self.calculate_center_on_token(
            x=target_x,
            y=target_y,
            token_id=token_id or None,
            character_id=char_id or None,
            duration_ms=duration_ms,
            easing=easing,
            reason="turn_started",
        )

    def handle_token_moved(
        self,
        event: TokenMoved | dict[str, Any],
        duration_ms: int | None = None,
        easing: str | None = None,
    ) -> CameraTarget:
        """Center camera on the action destination of a moved token."""
        if isinstance(event, dict):
            to_x = float(event.get("to_x", 0))
            to_y = float(event.get("to_y", 0))
            token_id = str(event.get("token_id") or "")
        else:
            to_x = float(event.to_x)
            to_y = float(event.to_y)
            token_id = str(event.token_id)

        return self.calculate_center_on_token(
            x=to_x,
            y=to_y,
            token_id=token_id,
            duration_ms=duration_ms,
            easing=easing,
            reason="token_moved",
        )

    def interpolate_position(
        self, start: CameraTarget, end: CameraTarget, progress: float
    ) -> tuple[float, float, float]:
        """Interpolate (x, y, zoom) between start and end camera targets at normalized progress [0, 1]."""
        p1x, p1y, p2x, p2y = parse_cubic_bezier(end.easing)
        eased_alpha = evaluate_cubic_bezier(p1x, p1y, p2x, p2y, progress)
        curr_x = start.target_x + eased_alpha * (end.target_x - start.target_x)
        curr_y = start.target_y + eased_alpha * (end.target_y - start.target_y)
        curr_zoom = start.zoom + eased_alpha * (end.zoom - start.zoom)
        return (curr_x, curr_y, curr_zoom)


# Session registry for Cinematic Director instances
_SESSION_DIRECTORS: dict[str, CinematicDirector] = {}


def get_cinematic_director(session_id: str) -> CinematicDirector:
    """Retrieve or initialize the Cinematic Director for a session."""
    if session_id not in _SESSION_DIRECTORS:
        _SESSION_DIRECTORS[session_id] = CinematicDirector()
    return _SESSION_DIRECTORS[session_id]


def clear_cinematic_directors() -> None:
    """Clear registered directors (for test cleanup)."""
    _SESSION_DIRECTORS.clear()


__all__ = [
    "DEFAULT_DURATION_MS",
    "DEFAULT_EASING",
    "DEFAULT_ZOOM",
    "CameraTarget",
    "CinematicDirector",
    "clear_cinematic_directors",
    "evaluate_cubic_bezier",
    "get_cinematic_director",
    "parse_cubic_bezier",
]
