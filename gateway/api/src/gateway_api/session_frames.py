"""Inbound frame contract for the session WebSocket (TASK-0810).

A client frame is a JSON object whose kind is its `type`, or its `action` when it has no `type`.
Mesh frames carry the kind in `type` and may carry a payload field named `action` (for example
`{"type": "token_action", "action": "cast"}`). The gateway relays only kinds in
`SESSION_FRAME_KINDS`. Other fields pass through unchanged, because each kind carries its own
payload.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

SESSION_FRAME_KINDS: frozenset[str] = frozenset(
    {
        "session_started",
        "player_readiness",
        "player_stand_in",
        "token_action",
        "aoe_placed",
        "spell_vfx",
        "confirm_ghost",
        "token_moved",
        "dice_rolled",
        "turn_advanced",
        "dm_whisper",
    }
)


class SessionFrame(BaseModel):
    """The envelope every inbound session frame must carry."""

    model_config = ConfigDict(extra="allow")

    type: str | None = None
    action: str | None = None

    @model_validator(mode="after")
    def _requires_a_kind(self) -> SessionFrame:
        if not (self.action or self.type):
            raise ValueError("a frame needs a type or an action")
        return self

    @property
    def kind(self) -> str:
        """The frame kind: `type`, else `action`. The validator guarantees one of them."""
        return str(self.type or self.action)


class InboundFrameError(Exception):
    """An inbound frame the gateway refuses. `code` names the error frame to send."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def read_session_frame(text: str) -> tuple[str, dict[str, Any]]:
    """Validate one inbound text frame. Return (kind, payload) for a known kind.

    The payload holds only the fields the client sent. Raises `InboundFrameError` with
    `INVALID_FRAME` for malformed JSON or a missing kind, and `UNKNOWN_FRAME` for an unknown kind.
    """
    try:
        frame = SessionFrame.model_validate_json(text)
    except ValidationError as exc:
        raise InboundFrameError(
            "INVALID_FRAME", "A frame must be a JSON object with a type or an action"
        ) from exc
    if frame.kind not in SESSION_FRAME_KINDS:
        raise InboundFrameError("UNKNOWN_FRAME", "Unknown frame type")
    return frame.kind, frame.model_dump(mode="json", exclude_unset=True)


__all__ = [
    "SESSION_FRAME_KINDS",
    "InboundFrameError",
    "SessionFrame",
    "read_session_frame",
]
