"""Campaign aggregate: create and edit a campaign. Owner is fixed at creation.

Governed by ADR-0011 (DeclarativeAggregate, @handles) and ADR-0015 decision (a).
"""

from __future__ import annotations

from typing import Any

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.events import CampaignCreated, CampaignUpdated

UPDATABLE_FIELDS = frozenset(
    {"title", "description", "setting", "system", "cover_image_url", "status", "settings"}
)


class CampaignState(BaseModel):
    """Event-sourced campaign record."""

    campaign_id: str = ""
    title: str = ""
    description: str = ""
    setting: str = ""
    system: str = "5e"
    status: str = "active"
    owner_id: str = ""
    cover_image_url: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


class CampaignAggregate(DeclarativeAggregate[CampaignState]):
    """Campaign lifecycle: creation and settings updates."""

    aggregate_type = "Campaign"
    requires_creation_event = True

    def create(
        self,
        *,
        title: str,
        owner_id: str,
        description: str = "",
        setting: str = "",
        system: str = "5e",
        cover_image_url: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> None:
        if self.is_created:
            raise ValueError(f"Campaign {self.aggregate_id} already exists")
        self.create_event(
            CampaignCreated,
            campaign_id=self.aggregate_id,
            owner_id=owner_id,
            title=title,
            description=description,
            setting=setting,
            system=system,
            cover_image_url=cover_image_url,
            settings=settings or {},
        )

    def update(self, changes: dict[str, Any]) -> None:
        """Apply the non-empty fields in `changes`. An empty set emits no event."""
        unknown = set(changes) - UPDATABLE_FIELDS
        if unknown:
            raise ValueError(f"Fields not updatable: {sorted(unknown)}")
        if not changes:
            return
        self.create_event(CampaignUpdated, campaign_id=self.aggregate_id, changes=changes)

    @handles(CampaignCreated)
    def _on_created(self, event: CampaignCreated) -> None:
        stamp = event.occurred_at.isoformat()
        self._state = CampaignState(
            campaign_id=str(self.aggregate_id),
            title=event.title,
            description=event.description,
            setting=event.setting,
            system=event.system,
            owner_id=event.owner_id,
            cover_image_url=event.cover_image_url,
            settings=dict(event.settings),
            created_at=stamp,
            updated_at=stamp,
        )

    @handles(CampaignUpdated)
    def _on_updated(self, event: CampaignUpdated) -> None:
        state = self.state
        for name, value in event.changes.items():
            setattr(state, name, value)
        state.updated_at = event.occurred_at.isoformat()
