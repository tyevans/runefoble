"""Stored state events for DM pending actions, whispers, and disambiguations (TASK-0568).

These events are appended to the event store by the copilot aggregates (Hard Invariant 2).
They are not published to the watcher stream. The public decision events live in
``actions.py`` and ``narrative.py``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event

PENDING_ACTIONS_AGGREGATE = "WatcherPendingActions"
WHISPERS_AGGREGATE = "WatcherWhispers"
DISAMBIGUATIONS_AGGREGATE = "WatcherDisambiguations"


@register_event("runefoble.events.watcher.pending_action_proposed")
class PendingActionProposed(BaseRunefobleEvent):
    aggregate_type: str = PENDING_ACTIONS_AGGREGATE
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.pending_action_proposed"
    action: dict[str, Any]


@register_event("runefoble.events.watcher.pending_action_vetoed")
class PendingActionVetoed(BaseRunefobleEvent):
    aggregate_type: str = PENDING_ACTIONS_AGGREGATE
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.pending_action_vetoed"
    action_id: str
    vetoed_by: str
    reason: str = ""


@register_event("runefoble.events.watcher.pending_action_approved")
class PendingActionApproved(BaseRunefobleEvent):
    aggregate_type: str = PENDING_ACTIONS_AGGREGATE
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.pending_action_approved"
    action_id: str
    approved_by: str


@register_event("runefoble.events.watcher.pending_action_modified")
class PendingActionModified(BaseRunefobleEvent):
    aggregate_type: str = PENDING_ACTIONS_AGGREGATE
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.pending_action_modified"
    action_id: str
    modified_by: str
    description: str
    target: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.watcher.pending_action_expired")
class PendingActionExpired(BaseRunefobleEvent):
    aggregate_type: str = PENDING_ACTIONS_AGGREGATE
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.pending_action_expired"
    action_id: str


@register_event("runefoble.events.watcher.whisper_recorded")
class WhisperRecorded(BaseRunefobleEvent):
    aggregate_type: str = WHISPERS_AGGREGATE
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.whisper_recorded"
    whisper: dict[str, Any]


@register_event("runefoble.events.watcher.disambiguation_opened")
class DisambiguationOpened(BaseRunefobleEvent):
    aggregate_type: str = DISAMBIGUATIONS_AGGREGATE
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.disambiguation_opened"
    disambiguation: dict[str, Any]


@register_event("runefoble.events.watcher.disambiguation_resolved")
class DisambiguationResolved(BaseRunefobleEvent):
    aggregate_type: str = DISAMBIGUATIONS_AGGREGATE
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.disambiguation_resolved"
    disambiguation_id: str
    candidate_id: str


__all__ = [
    "DISAMBIGUATIONS_AGGREGATE",
    "PENDING_ACTIONS_AGGREGATE",
    "WHISPERS_AGGREGATE",
    "DisambiguationOpened",
    "DisambiguationResolved",
    "PendingActionApproved",
    "PendingActionExpired",
    "PendingActionModified",
    "PendingActionProposed",
    "PendingActionVetoed",
    "WhisperRecorded",
]
