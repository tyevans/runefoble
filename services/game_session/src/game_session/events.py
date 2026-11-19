"""The session event-to-stream mapping for the game session repository.

Every event that the session aggregate commits is published by the repository itself.
The mapping below is the only place that chooses the stream for a session event family.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from eventsource.domain.event import DomainEvent
from game_session.shared.streams import STREAM_SESSION, STREAM_WATCHER
from runefoble_events.events import (
    AtmosphereUpdated,
    CharacterControlTransferred,
    CharacterSelectedForLobby,
    CombatEncounterEnded,
    CombatEncounterStarted,
    CombatRoundAdvanced,
    CombatTurnPausedForReactionEvent,
    DiceRolled,
    DMOverrideApplied,
    InitiativeRolled,
    InitiativeTurnAdvanced,
    PlayerJoinedSession,
    PlayerLeftSession,
    ReactionResolvedEvent,
    ReadinessToggled,
    ReadyActionRegisteredEvent,
    ReadyActionTriggeredEvent,
    SessionCreated,
    SessionEnded,
    SessionStarted,
    StandInActionDecided,
    TurnAdvanced,
    TurnStarted,
    WeatherChanged,
)
from runefoble_platform.event_publish import publish_or_fail

SESSION_EVENT_STREAMS: dict[type[DomainEvent], str] = {
    SessionCreated: STREAM_SESSION,
    SessionStarted: STREAM_SESSION,
    PlayerJoinedSession: STREAM_SESSION,
    PlayerLeftSession: STREAM_SESSION,
    ReadinessToggled: STREAM_SESSION,
    CharacterSelectedForLobby: STREAM_SESSION,
    TurnAdvanced: STREAM_SESSION,
    SessionEnded: STREAM_SESSION,
    CharacterControlTransferred: STREAM_SESSION,
    DiceRolled: STREAM_SESSION,
    CombatEncounterStarted: STREAM_SESSION,
    InitiativeRolled: STREAM_SESSION,
    InitiativeTurnAdvanced: STREAM_SESSION,
    CombatRoundAdvanced: STREAM_SESSION,
    TurnStarted: STREAM_SESSION,
    CombatEncounterEnded: STREAM_SESSION,
    CombatTurnPausedForReactionEvent: STREAM_SESSION,
    ReactionResolvedEvent: STREAM_SESSION,
    ReadyActionRegisteredEvent: STREAM_SESSION,
    ReadyActionTriggeredEvent: STREAM_SESSION,
    DMOverrideApplied: STREAM_SESSION,
    AtmosphereUpdated: STREAM_SESSION,
    WeatherChanged: STREAM_SESSION,
    StandInActionDecided: STREAM_WATCHER,
}


class UnmappedSessionEventError(RuntimeError):
    """Raised when the session repository commits an event family with no stream mapping."""


def stream_for_session_event(event: DomainEvent) -> str:
    """Return the stream that a committed session event is published to."""
    try:
        return SESSION_EVENT_STREAMS[type(event)]
    except KeyError as exc:
        raise UnmappedSessionEventError(
            f"No stream mapping for session event '{type(event).__name__}'"
        ) from exc


class SessionEventPublisher:
    """Publishes each committed session event to its mapped stream.

    The bus is resolved on each call, so the repository works before and after the bus
    is configured. A missing bus skips publication, as in the other game session routes.
    A publish failure raises DomainEventPublishError, which the API maps to HTTP 503.
    """

    def __init__(self, bus_provider: Callable[[], Any]) -> None:
        self._bus_provider = bus_provider

    async def publish(self, events: Sequence[DomainEvent]) -> None:
        bus = self._bus_provider()
        if bus is None:
            return
        for event in events:
            await publish_or_fail(bus, stream_for_session_event(event), event)
