"""Watcher actions, DM co-pilot review, and action disambiguation domain events."""

from __future__ import annotations

from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.voice.audio_conditioned")
class VoiceAudioConditioned(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.audio_conditioned"
    session_id: str
    speaker_id: str
    speaker_name: str
    filters_applied: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    audio_bytes_length: int = 0


@register_event("runefoble.events.watcher.action_proposed")
class WatcherActionProposed(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "GameSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.action_proposed"
    action_id: str
    session_id: str
    campaign_id: str = ""
    actor_name: str
    action_type: str
    description: str
    target: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    pause_window_ms: int = 2000


@register_event("runefoble.events.watcher.action_vetoed")
class WatcherActionVetoed(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "GameSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.action_vetoed"
    action_id: str
    session_id: str
    campaign_id: str = ""
    vetoed_by: str
    reason: str = ""
    original_action: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.watcher.action_approved")
class WatcherActionApproved(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "GameSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.action_approved"
    action_id: str
    session_id: str
    campaign_id: str = ""
    approved_by: str
    action_type: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.watcher.action_modified")
class WatcherActionModified(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "GameSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.action_modified"
    action_id: str
    session_id: str
    campaign_id: str = ""
    modified_by: str
    description: str = ""
    target: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.watcher.disambiguation_requested")
class IntentDisambiguationRequested(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "GameSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.disambiguation_requested"
    session_id: str
    campaign_id: str | None = None
    speaker_id: str
    speaker_name: str
    original_transcript: str
    disambiguation_id: str
    action_type: str
    ambiguous_target: str
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    clarification_prompt: str


@register_event("runefoble.events.watcher.compound_action_resolved")
class CompoundActionResolved(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "GameSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.compound_action_resolved"
    session_id: str
    campaign_id: str | None = None
    speaker_id: str
    speaker_name: str
    original_transcript: str
    disambiguation_id: str | None = None
    resolved_target: str | None = None
    actions: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "ready"
    narrative_summary: str = ""


__all__ = [
    "CompoundActionResolved",
    "IntentDisambiguationRequested",
    "VoiceAudioConditioned",
    "WatcherActionApproved",
    "WatcherActionModified",
    "WatcherActionProposed",
    "WatcherActionVetoed",
]
