"""Event-sourced open disambiguation requests, one aggregate per game session (TASK-0568)."""

from __future__ import annotations

from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid5

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.watcher_events.copilot_state import (
    DISAMBIGUATIONS_AGGREGATE,
    DisambiguationOpened,
    DisambiguationResolved,
)
from the_watcher.copilot_state.errors import CopilotStateError
from the_watcher.models import CandidateTarget, CompoundActionNode


def disambiguation_board_id(session_id: str) -> UUID:
    """Return the stable aggregate id of one session's open disambiguations."""
    return uuid5(NAMESPACE_DNS, f"disambiguation-board:{session_id}")


class DisambiguationNotFoundError(CopilotStateError):
    """No open disambiguation with this id exists in the session."""


class PendingDisambiguation(BaseModel):
    """An ambiguous target that waits for the player to choose a candidate."""

    disambiguation_id: str
    session_id: str
    campaign_id: str | None
    speaker_id: str
    speaker_name: str
    transcript: str
    action_type: str
    ambiguous_target: str
    candidates: list[CandidateTarget] = Field(default_factory=list)
    clarification_prompt: str
    actions: list[CompoundActionNode] = Field(default_factory=list)


class DisambiguationBoardState(BaseModel):
    """Open disambiguations of one session, keyed by disambiguation id."""

    session_id: str = ""
    open: dict[str, PendingDisambiguation] = Field(default_factory=dict)


class DisambiguationAggregate(DeclarativeAggregate[DisambiguationBoardState]):
    """Owns the open disambiguation requests of one game session."""

    aggregate_type = DISAMBIGUATIONS_AGGREGATE

    def __init__(self, aggregate_id: UUID | None = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = DisambiguationBoardState()

    @handles(DisambiguationOpened)
    def _on_opened(self, event: DisambiguationOpened) -> None:
        pending = PendingDisambiguation.model_validate(event.disambiguation)
        self.state.session_id = pending.session_id
        self.state.open[pending.disambiguation_id] = pending

    @handles(DisambiguationResolved)
    def _on_resolved(self, event: DisambiguationResolved) -> None:
        self.state.open.pop(event.disambiguation_id, None)

    def find(self, disambiguation_id: str) -> PendingDisambiguation | None:
        """Return the open request, or None when it is unknown or already resolved."""
        return self.state.open.get(disambiguation_id)

    def open_request(self, pending: PendingDisambiguation) -> None:
        """Record a new disambiguation request."""
        self.create_event(DisambiguationOpened, disambiguation=pending.model_dump(mode="json"))

    def resolve(self, disambiguation_id: str, candidate_id: str) -> None:
        """Close an open request with the candidate the player chose."""
        if disambiguation_id not in self.state.open:
            raise DisambiguationNotFoundError(
                f"Disambiguation '{disambiguation_id}' is not open in this session."
            )
        self.create_event(
            DisambiguationResolved,
            disambiguation_id=disambiguation_id,
            candidate_id=candidate_id,
        )
