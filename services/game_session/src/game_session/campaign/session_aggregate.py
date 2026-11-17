"""Campaign sessions aggregate: the sessions and staging lobbies of one campaign.

One stream per campaign, so the list is read from the event store on every request.
Governed by ADR-0011 and ADR-0015 decision (a).
"""

from __future__ import annotations

from typing import Any

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.campaign_lifecycle import CampaignSessionCreated


class CampaignSessionRecord(BaseModel):
    id: str
    title: str
    status: str
    scheduled_at: str | None = None
    description: str = ""
    created_at: str


class CampaignSessionsState(BaseModel):
    campaign_id: str = ""
    sessions: list[CampaignSessionRecord] = Field(default_factory=list)


class CampaignSessionsAggregate(DeclarativeAggregate[CampaignSessionsState]):
    """Adds sessions to a campaign. Lists are read from the state the events build."""

    aggregate_type = "CampaignSessions"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = CampaignSessionsState(campaign_id=str(aggregate_id or ""))

    def add_session(
        self,
        *,
        session_id: str,
        title: str,
        status: str,
        scheduled_at: str | None,
        description: str,
    ) -> None:
        self.create_event(
            CampaignSessionCreated,
            campaign_id=self.aggregate_id,
            session_id=session_id,
            title=title,
            status=status,
            scheduled_at=scheduled_at,
            description=description,
        )

    @handles(CampaignSessionCreated)
    def _on_created(self, event: CampaignSessionCreated) -> None:
        self.state.sessions.append(
            CampaignSessionRecord(
                id=event.session_id,
                title=event.title,
                status=event.status,
                scheduled_at=event.scheduled_at,
                description=event.description,
                created_at=event.occurred_at.isoformat(),
            )
        )
