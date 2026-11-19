"""Camera target wire model. The board aggregate stores one target per session."""

from __future__ import annotations

from pydantic import BaseModel, Field

DEFAULT_EASING = "cubic-bezier(0.25, 0.1, 0.25, 1.0)"
DEFAULT_DURATION_MS = 300
DEFAULT_ZOOM = 1.5


class CameraTarget(BaseModel):
    """Cinematic camera viewport target for OBS stream and spectator clients."""

    target_x: float = Field(default=0.0, description="Centered grid x-coordinate")
    target_y: float = Field(default=0.0, description="Centered grid y-coordinate")
    zoom: float = Field(default=1.0, description="Viewport zoom multiplier")
    duration_ms: int = Field(default=DEFAULT_DURATION_MS, description="Transition duration in ms")
    easing: str = Field(default=DEFAULT_EASING, description="Cubic-bezier easing curve string")
    active_token_id: str | None = Field(default=None, description="Active focused token ID")
    active_character_id: str | None = Field(default=None, description="Active focused character ID")
    reason: str = Field(default="init", description="Trigger reason (turn_started, token_moved)")
    timestamp: str = Field(default="", description="When the focus was recorded (ISO 8601)")

    @classmethod
    def initial(cls) -> CameraTarget:
        """Return the target that a session holds before any focus event."""
        return cls()
