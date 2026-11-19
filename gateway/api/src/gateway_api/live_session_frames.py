"""Server session frames built from published domain events (TASK-0923).

The gateway does not accept these kinds from clients (TASK-0910). It builds them from the
events that the owner publishes:

- `turn_advanced` from `TurnAdvanced` (game_session, `runefoble.events.session`).
- `dice_rolled` from `DiceRolled` (game_session, `runefoble.events.session`).

Other events on the stream give no frame. `token_moved` is not built here: board_state sends it
on its own board socket. `dm_whisper` is not built here: no service publishes a whisper event.
"""

from __future__ import annotations

from typing import Any

from runefoble_events.events import DiceRolled, TurnAdvanced


class LiveFrameError(ValueError):
    """A mapped event that cannot become a frame, for example one with no session id."""


def _session_key(event: Any) -> str:
    session_id = getattr(event, "session_id", None)
    if not session_id:
        raise LiveFrameError(f"{type(event).__name__} {event.event_id} has no session_id")
    return str(session_id)


def live_frame_for(event: Any) -> tuple[str, dict[str, Any]] | None:
    """Return (session id, frame) for an event that has a session frame, else None.

    Raises `LiveFrameError` for a mapped event without a session id, so the consumer sends the
    message to the dead-letter stream.
    """
    if isinstance(event, TurnAdvanced):
        session_id = _session_key(event)
        active = event.active_character_id
        return session_id, {
            "type": "turn_advanced",
            "sessionId": session_id,
            "previousTurn": event.previous_turn,
            "newTurn": event.new_turn,
            "activeCharacterId": str(active) if active is not None else None,
        }
    if isinstance(event, DiceRolled):
        session_id = _session_key(event)
        return session_id, {
            "type": "dice_rolled",
            "sessionId": session_id,
            "rollerId": event.roller_id,
            "rollerName": event.roller_name,
            "formula": event.formula,
            "total": event.total,
            "rolls": list(event.rolls),
            "isCrit": event.is_crit,
            "isFumble": event.is_fumble,
        }
    return None


__all__ = ["LiveFrameError", "live_frame_for"]
