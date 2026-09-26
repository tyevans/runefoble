"""Audience Studio and live spectator interactivity events."""

from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.audience.poll_started")
class AudiencePollStarted(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "AudiencePoll"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.audience.poll_started"
    poll_id: UUID | str
    campaign_id: UUID | str
    session_id: UUID | str | None = None
    title: str
    prompt: str
    options: list[dict[str, Any]] = Field(default_factory=list)
    duration_seconds: int = 60
    quorum: int = 5
    expires_at: str = ""


@register_event("runefoble.events.audience.vote_cast")
class AudienceVoteCast(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "AudiencePoll"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.audience.vote_cast"
    poll_id: UUID | str
    campaign_id: UUID | str
    voter_id: str
    option_id: str
    channel: str = "web"
    timestamp: str = ""


@register_event("runefoble.events.audience.poll_completed")
class AudiencePollCompleted(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "AudiencePoll"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.audience.poll_completed"
    poll_id: UUID | str
    campaign_id: UUID | str
    session_id: UUID | str | None = None
    winning_option_id: str | None = None
    winning_option_label: str | None = None
    total_votes: int = 0
    quorum_met: bool = False
    proposed_modifier: dict[str, Any] | None = None


@register_event("runefoble.events.audience.modifier_proposed")
class AudienceModifierProposed(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "AudiencePoll"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.audience.modifier_proposed"
    proposal_id: UUID | str
    poll_id: UUID | str
    campaign_id: UUID | str
    session_id: UUID | str | None = None
    title: str
    modifier_type: str = "chaos_modifier"
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"


@register_event("runefoble.events.audience.modifier_approved")
class AudienceModifierApproved(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "AudiencePoll"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.audience.modifier_approved"
    proposal_id: UUID | str
    poll_id: UUID | str
    campaign_id: UUID | str
    session_id: UUID | str | None = None
    approved_by: str
    approved: bool = True
    modifier_type: str = "chaos_modifier"
    parameters: dict[str, Any] = Field(default_factory=dict)
    applied_at: str = ""
