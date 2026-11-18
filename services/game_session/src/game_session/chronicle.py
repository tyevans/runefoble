"""Read projections over a game session: the chronicle feed and the absentee recap (TASK-0641).

The feed reads the session's own event stream from the event store (ADR-0011). It keeps only
the event kinds that the App Shell shows. The absentee recap derives from the stand-in actions
that the session aggregate recorded from `StandInActionDecided`. Neither projection writes state
and neither holds fixed sample content.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from eventsource.domain.event import DomainEvent
from eventsource.domain.stream_id import StreamId
from game_session.dependencies import repo
from game_session.models import GameSessionState
from pydantic import BaseModel, Field
from runefoble_events.events import DiceRolled, SessionEnded, SessionStarted, StandInActionDecided

ChronicleKind = Literal["stand_in_action", "dice_roll", "session_started", "session_ended"]


class ChronicleEntry(BaseModel):
    """One feed line. `penalties` lists the penalties the Watcher applied on a stand-in turn."""

    event_id: str
    kind: ChronicleKind
    occurred_at: datetime
    speaker: str
    text: str
    action_type: str | None = None
    penalties: list[str] = Field(default_factory=list)


class AbsenteePenalty(BaseModel):
    character_name: str
    penalty: str


class StandInTurnSummary(BaseModel):
    character_name: str
    action_type: str
    dialogue: str
    penalties: list[str] = Field(default_factory=list)
    flavor_text: str = ""


class AbsenteeRecap(BaseModel):
    session_id: UUID
    stand_in_turns: int
    penalties: list[AbsenteePenalty] = Field(default_factory=list)
    actions: list[StandInTurnSummary] = Field(default_factory=list)


def _chronicle_entry(event_id: str, event: DomainEvent) -> ChronicleEntry | None:
    """Map one committed session event to a feed line. Return None for other event kinds."""
    occurred_at = event.occurred_at
    if isinstance(event, StandInActionDecided):
        return ChronicleEntry(
            event_id=event_id,
            kind="stand_in_action",
            occurred_at=occurred_at,
            speaker=event.character_name,
            text=event.dialogue,
            action_type=event.action_type,
            penalties=list(event.penalties_applied),
        )
    if isinstance(event, DiceRolled):
        return ChronicleEntry(
            event_id=event_id,
            kind="dice_roll",
            occurred_at=occurred_at,
            speaker=event.roller_name,
            text=f"{event.formula} = {event.total}",
            action_type="dice_roll",
        )
    if isinstance(event, SessionStarted):
        return ChronicleEntry(
            event_id=event_id,
            kind="session_started",
            occurred_at=occurred_at,
            speaker="system",
            text="Session started.",
        )
    if isinstance(event, SessionEnded):
        return ChronicleEntry(
            event_id=event_id,
            kind="session_ended",
            occurred_at=occurred_at,
            speaker="system",
            text=event.summary,
        )
    return None


async def read_session_chronicle(session_id: UUID) -> list[ChronicleEntry]:
    """Return the feed lines of one session in commit order. An empty stream yields no lines."""
    stream = StreamId(aggregate_id=session_id, category=repo.aggregate_type)
    entries: list[ChronicleEntry] = []
    async for envelope in repo.event_store.read_stream(stream):
        entry = _chronicle_entry(str(envelope.event.event_id), envelope.event)
        if entry is not None:
            entries.append(entry)
    return entries


def build_absentee_recap(state: GameSessionState) -> AbsenteeRecap:
    """Summarise the stand-in turns that the session recorded. No turns yields an empty recap."""
    actions = [_summarise_turn(action) for action in state.stand_in_actions]
    penalties = [
        AbsenteePenalty(character_name=action.character_name, penalty=penalty)
        for action in actions
        for penalty in action.penalties
    ]
    return AbsenteeRecap(
        session_id=state.session_id,
        stand_in_turns=len(actions),
        penalties=penalties,
        actions=actions,
    )


def _summarise_turn(action: dict[str, Any]) -> StandInTurnSummary:
    return StandInTurnSummary(
        character_name=str(action.get("character_name", "")),
        action_type=str(action.get("action_type", "")),
        dialogue=str(action.get("dialogue", "")),
        penalties=[str(p) for p in action.get("penalties_applied", [])],
        flavor_text=str(action.get("flavor_text", "")),
    )
