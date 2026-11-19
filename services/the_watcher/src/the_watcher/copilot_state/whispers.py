"""Event-sourced DM whisper log, one aggregate per session and recipient (TASK-0568)."""

from __future__ import annotations

from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid5

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.events import WHISPERS_AGGREGATE, WhisperDispatched, WhisperRecorded
from the_watcher.models import WhisperSuggestion

DEFAULT_RECIPIENT_ROLE = "dungeon_master"


def whisper_log_id(session_id: str, recipient_role: str = DEFAULT_RECIPIENT_ROLE) -> UUID:
    """Return the stable aggregate id of one session's whisper channel for a recipient."""
    return uuid5(NAMESPACE_DNS, f"whisper-log:{session_id}:{recipient_role}")


class WhisperLogState(BaseModel):
    """Whispers recorded for one session channel, in the order they were written."""

    session_id: str = ""
    recipient_role: str = DEFAULT_RECIPIENT_ROLE
    whispers: list[WhisperSuggestion] = Field(default_factory=list)


class WhisperAggregate(DeclarativeAggregate[WhisperLogState]):
    """Owns the whisper log of one session and recipient."""

    aggregate_type = WHISPERS_AGGREGATE

    def __init__(self, aggregate_id: UUID | None = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = WhisperLogState()

    @handles(WhisperRecorded)
    def _on_recorded(self, event: WhisperRecorded) -> None:
        whisper = WhisperSuggestion.model_validate(event.whisper)
        self.state.session_id = whisper.session_id
        self.state.recipient_role = whisper.recipient_role
        self.state.whispers.append(whisper)

    @handles(WhisperDispatched)
    def _on_dispatched(self, event: WhisperDispatched) -> None:
        whisper = self.find(event.whisper_id)
        if whisper is None:
            raise ValueError(f"Whisper {event.whisper_id} is not in this log.")
        whisper.metadata["dispatched"] = True
        whisper.metadata["dispatched_text"] = event.text

    def record(self, whisper: WhisperSuggestion) -> None:
        """Append one whisper to the log."""
        self.create_event(WhisperRecorded, whisper=whisper.model_dump(mode="json"))

    def find(self, whisper_id: str) -> WhisperSuggestion | None:
        """Return the whisper with this id, or None when the log has no such whisper."""
        for whisper in self.state.whispers:
            if whisper.whisper_id == whisper_id:
                return whisper
        return None

    def mark_dispatched(self, whisper_id: str, text: str) -> None:
        """Record that the DM sent this whisper to the table, with the text that was sent."""
        self.create_event(WhisperDispatched, whisper_id=whisper_id, text=text)
