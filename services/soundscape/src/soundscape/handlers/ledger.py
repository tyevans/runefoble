"""Ledger of handled source events for the Soundscape aggregate (TASK-0854).

A stream message can be delivered twice. The ledger keeps the ids of the source events whose
effects this aggregate already saved. The ledger is bounded: it keeps the most recent
``SOURCE_LEDGER_LIMIT`` ids per session. A redelivery older than that window is not
recognised, so its effects would apply again. Reclaim redelivers only messages that stayed
pending for the minimum idle time, so the window covers that case.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eventsource.domain.decorators import handles
from runefoble_events.soundscape import SoundscapeSourceEventHandled

if TYPE_CHECKING:
    from soundscape.aggregate import SoundscapeState

SOURCE_LEDGER_LIMIT = 1000


class SourceLedgerHandlersMixin:
    """Mixin that records and reads the handled source event ids."""

    _state: SoundscapeState | None
    state: SoundscapeState
    aggregate_id: Any
    create_event: Any
    init_state: Any

    def record_source_event(self, session_id: str, source_event_id: str) -> None:
        """Record that the effects of one source event are saved with this aggregate."""
        self.create_event(
            SoundscapeSourceEventHandled,
            aggregate_id=self.aggregate_id,
            session_id=session_id,
            source_event_id=source_event_id,
        )

    def has_handled_source_event(self, source_event_id: str) -> bool:
        return source_event_id in self.state.handled_source_event_ids

    @handles(SoundscapeSourceEventHandled)
    def _on_source_event_handled(self, event: SoundscapeSourceEventHandled) -> None:
        if self._state is None:
            self._state = self.init_state()
        ids = [*self.state.handled_source_event_ids, event.source_event_id]
        self.state.handled_source_event_ids = ids[-SOURCE_LEDGER_LIMIT:]


__all__ = ["SOURCE_LEDGER_LIMIT", "SourceLedgerHandlersMixin"]
