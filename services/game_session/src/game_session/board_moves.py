"""Redis Streams handler that records board token moves in the session chronicle.

board_state owns the board and publishes `TokenMoved` on `runefoble.events.board`. The session
chronicle is the feed of game_session, so game_session records the move on the session
aggregate as `TokenMoveChronicled` (ADR-0006, ADR-0011). Other board events are ignored. A move
whose session game_session does not know raises, so the message is dead-lettered (ADR-0015).
"""

from __future__ import annotations

from typing import Any

from game_session.aggregate import GameSessionAggregate
from runefoble_events.events import TokenMoved
from runefoble_platform.aggregate_loading import load_if_exists
from runefoble_platform.event_sourcing import AggregateRepository

BOARD_STREAM = "runefoble.events.board"


class UnchronicledMoveError(ValueError):
    """A `TokenMoved` event that names no session or a session that game_session does not know."""


async def chronicle_board_move(event: Any, repo: AggregateRepository[GameSessionAggregate]) -> None:
    """Record one board move on its session. A redelivered move records nothing."""
    if not isinstance(event, TokenMoved):
        return
    if event.session_id is None:
        raise UnchronicledMoveError(f"TokenMoved {event.event_id} has no session_id.")
    session = await load_if_exists(repo, event.session_id)
    if session is None:
        raise UnchronicledMoveError(
            f"TokenMoved {event.event_id} names unknown session {event.session_id}."
        )
    source_event_id = str(event.event_id)
    if source_event_id in session.state.chronicled_move_ids:
        # A redelivery. The chronicle already holds this move, so nothing changes.
        return
    session.chronicle_token_move(
        source_event_id=source_event_id,
        token_id=event.token_id,
        token_name=event.name,
        to=(event.to_x, event.to_y),
        initiated_by=event.initiated_by,
    )
    await repo.save(session)
