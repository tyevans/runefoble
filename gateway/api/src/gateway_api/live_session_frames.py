"""Server session frames built from published domain events (TASK-0923, TASK-0927).

The gateway does not accept these kinds from clients (TASK-0910). It builds them from the
events that the owner publishes:

- `turn_advanced` from `TurnAdvanced` (game_session, `runefoble.events.session`).
- `dice_rolled` from `DiceRolled` (game_session, `runefoble.events.session`).
- `chronicle_entry` from `TokenMoveChronicled` (game_session, `runefoble.events.session`). The
  `entry` is the line that `GET /api/v1/sessions/{id}/events` returns for the event.
- `dm_whisper` from `WhisperRecorded` (the_watcher, `runefoble.events.watcher`). This frame is
  for the DM only: it goes to the sockets whose caller holds `session.control`.

Other events on the streams give no frame. `token_moved` is not built here: board_state sends
it on its own board socket. The chronicle line of that move comes as `chronicle_entry`.
"""

from __future__ import annotations

from typing import Any, NamedTuple

from runefoble_events.events import DiceRolled, TokenMoveChronicled, TurnAdvanced, WhisperRecorded


class LiveFrame(NamedTuple):
    """One frame for the sockets of one session. `dm_only` frames go to DM sockets only."""

    session_id: str
    frame: dict[str, Any]
    dm_only: bool = False


class LiveFrameError(ValueError):
    """A mapped event that cannot become a frame, for example one with no session id."""


def _session_key(event: Any) -> str:
    session_id = getattr(event, "session_id", None)
    if not session_id:
        raise LiveFrameError(f"{type(event).__name__} {event.event_id} has no session_id")
    return str(session_id)


def _whisper_frame(event: WhisperRecorded) -> LiveFrame:
    whisper = dict(event.whisper)
    session_id = whisper.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise LiveFrameError(f"WhisperRecorded {event.event_id} has no whisper session_id")
    return LiveFrame(
        session_id,
        {"type": "dm_whisper", "sessionId": session_id, "whisper": whisper},
        dm_only=True,
    )


def _move_entry_frame(event: TokenMoveChronicled) -> LiveFrame:
    session_id = _session_key(event)
    entry = {
        "event_id": str(event.event_id),
        "kind": "token_moved",
        "occurred_at": event.model_dump(mode="json")["occurred_at"],
        "speaker": event.token_name,
        "text": event.line,
        "action_type": "board_move",
        "penalties": [],
    }
    return LiveFrame(
        session_id, {"type": "chronicle_entry", "sessionId": session_id, "entry": entry}
    )


def live_frame_for(event: Any) -> LiveFrame | None:
    """Return the session frame of an event that has one, else None.

    Raises `LiveFrameError` for a mapped event without a session id, so the consumer sends the
    message to the dead-letter stream.
    """
    if isinstance(event, TurnAdvanced):
        session_id = _session_key(event)
        active = event.active_character_id
        return LiveFrame(
            session_id,
            {
                "type": "turn_advanced",
                "sessionId": session_id,
                "previousTurn": event.previous_turn,
                "newTurn": event.new_turn,
                "activeCharacterId": str(active) if active is not None else None,
            },
        )
    if isinstance(event, DiceRolled):
        session_id = _session_key(event)
        return LiveFrame(
            session_id,
            {
                "type": "dice_rolled",
                "sessionId": session_id,
                "rollerId": event.roller_id,
                "rollerName": event.roller_name,
                "formula": event.formula,
                "total": event.total,
                "rolls": list(event.rolls),
                "isCrit": event.is_crit,
                "isFumble": event.is_fumble,
            },
        )
    if isinstance(event, TokenMoveChronicled):
        return _move_entry_frame(event)
    if isinstance(event, WhisperRecorded):
        return _whisper_frame(event)
    return None


__all__ = ["LiveFrame", "LiveFrameError", "live_frame_for"]
